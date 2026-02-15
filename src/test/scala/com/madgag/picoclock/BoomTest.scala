package com.madgag.picoclock

import cats.*
import cats.effect.unsafe.implicits.global
import cats.kernel.Order.*
import com.github.tototoshi.csv.CSVWriter
import com.gu.time.duration.formatting.*
import com.madgag.logic.*
import com.madgag.logic.BoundedInterval.*
import com.madgag.logic.fileformat.Foo
import com.madgag.logic.fileformat.saleae.csv.SaleaeCsv
import com.madgag.logic.protocol.holtek.ht1632c.Channel.{ChipSelect, Clock, Data}
import com.madgag.logic.protocol.holtek.ht1632c.operations.*
import com.madgag.logic.protocol.holtek.ht1632c.operations.Command.COM.DisplayLayout.`24x16`
import com.madgag.logic.protocol.holtek.ht1632c.operations.Command.COM.OpenDrain.PMOS
import com.madgag.logic.protocol.holtek.ht1632c.operations.Command.Setting.OffOn.{Off, On}
import com.madgag.logic.protocol.holtek.ht1632c.operations.Command.Setting.Switchable
import com.madgag.logic.protocol.holtek.ht1632c.operations.Command.Setting.Switchable.{Blink, LedDutyCycleGenerator, SystemOscillator}
import com.madgag.logic.protocol.holtek.ht1632c.operations.Command.{COM, PWM, Setting, SyncRole}
import com.madgag.logic.protocol.holtek.ht1632c.operations.DataOperation.WriteMode
import com.madgag.logic.protocol.holtek.ht1632c.signals.TimingCharacteristics
import com.madgag.logic.protocol.holtek.ht1632c.{Channel, HoltekBits}
import com.madgag.logic.time.Time.*
import com.madgag.logic.time.TimedF.{dropTime, given}
import com.madgag.logic.time.{Time, TimeParser, Timed, TimedF}
import com.madgag.micropython.logiccapture.model.*
import com.madgag.picoclock.RemoteCaptureUtil.{deviceFS, remoteCaptureClient}
import org.scalatest.Inside.inside
import org.scalatest.Inspectors.forAll
import org.scalatest.OptionValues
import org.scalatest.concurrent.ScalaFutures
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should
import org.scalatest.time.{Millis, Seconds, Span}
import scodec.bits.BitVector

import java.time.temporal.ChronoUnit.NANOS
import scala.collection.immutable.SortedSet

class BoomTest extends AnyFlatSpec with should.Matchers with OptionValues with ScalaFutures {

  implicit override val patienceConfig: PatienceConfig = PatienceConfig(
    timeout = scaled(Span(300, Seconds)),
    interval = scaled(Span(500, Millis))
  )

  private val dataPin = GpioPin(2)

  val gpioMapping = ChannelMapping(
    "GP2" -> Data,
    "GP3" -> Clock.Write,
    "GP4" -> ChipSelect.Leader,
    "GP5" -> ChipSelect.Follower.One
  )
  
  "Running code to drive HolTek" should "see a valid sequence" in {
    val triggerPattern = Trigger.Pattern(BitVector.bits(Seq(true, false, true)), GpioPin(3))
    println(triggerPattern.stateByPin)
    whenReady(remoteCaptureClient.capture(JobDef(
      RemoteCaptureUtil.gitSource,
      Seq(
        ExecuteAndCaptureDef(
          ExecutionDef(deviceFS, "from capture_test import exec_with ; exec_with(100000)"),
          CaptureDef(
            Sampling(frequency = 200000, preTriggerSamples = 10, postTriggerSamples = 380000),
            SortedSet(dataPin, GpioPin(3), GpioPin(4), GpioPin(5)),
            triggerPattern
          )
        )
      )
    ), gpioMapping).value.map(_.left.map(err => new RuntimeException(err.toString)).toTry.get).unsafeToFuture()) { signals =>
      val sig = signals.head.value
      val deglitchedSignal = sig // sig.transform(_.deglitch(ofNanos(90))) - Pico signals don't seem to need de-glitching
      writeOutFileForReference(deglitchedSignal)
      val anomaliesByCriterion = TimingCharacteristics.violationFinder.violationsIn(deglitchedSignal)
      println(anomaliesByCriterion.map {
        case (key, value) => key.name + ":\n\t" + value.toSeq.take(3).map(_.summary).mkString(", ")
      }.mkString("\n"))
      require(anomaliesByCriterion.isEmpty)
      val opSignals: TimedDistributedOperations[Delta] = HoltekBits.operationsFor(deglitchedSignal)

      val initSeq: Seq[(ChipSelect, CommandMode)] =
        initSequence(ChipSelect.Leader, SyncRole.RCLeader).zip(initSequence(ChipSelect.Follower.One, SyncRole.Follower)).flatMap { (x, y) => Seq(x, y) }

      val (initiationCommands, writeCommands) = opSignals.mapK(dropTime).ops.splitAt(initSeq.size)

      initiationCommands shouldBe initSeq

      val opSignalsReally = operationsFor(deglitchedSignal)


      val writesWithTimes = opSignals.ops.drop(initSeq.size)
      writesWithTimes.size shouldBe > (10)
      forAll(writesWithTimes.take(10).map(_.value._2)) { c =>
        inside(c) {
          case writeMode: WriteMode => writeMode.writesByLedAddress should have size 384
        }
      }

      val startTimes = writesWithTimes.map(_.interval.lowerValueBound.a)
      val durations = startTimes.zip(startTimes.tail).map(Time.between)
      println(durations.map(_.format(1, NANOS)))
    }
  }

  def operationsFor[T: Time](channelSignals: ChannelSignals[T, Channel]): Seq[Timed[T, (ChipSelect, OperationSignals[T])]] =
    (for {
      chipSelectChannel <- channelSignals.data.keySet.collect { case cs: ChipSelect => cs }.toSeq
      opSignal <- HoltekBits.operationSignalsFor(channelSignals, chipSelectChannel)
      boundedInterval <- opSignal.interval.toBoundedIntervalOpt.toSeq
    } yield Timed(boundedInterval, chipSelectChannel -> opSignal)).sortBy(_.interval.lowerValueBound.a)

  def initSequence(chipSelect: ChipSelect, syncRole: SyncRole): Seq[(ChipSelect, CommandMode)] = Seq(
    CommandMode(SystemOscillator(Off), COM(PMOS, `24x16`), syncRole, SystemOscillator(On), PWM(16), Blink(Off), LedDutyCycleGenerator(Off)),
    CommandMode(LedDutyCycleGenerator(Off)),
    CommandMode(SystemOscillator(Off)),
    CommandMode(SystemOscillator(On)),
    CommandMode(LedDutyCycleGenerator(On))
  ).map(chipSelect -> _)

  private def writeOutFileForReference(deglitchedSignal: ChannelSignals[Delta, Channel]): Unit = {
    val tmpFile = os.temp(deleteOnExit = false).toIO
    Foo.write(deglitchedSignal, SaleaeCsv.csvDetails(TimeParser.DeltaParser, gpioMapping))(CSVWriter.open(tmpFile)(SaleaeCsv.CsvFormat))
    println(tmpFile.getAbsolutePath)
  }
}

