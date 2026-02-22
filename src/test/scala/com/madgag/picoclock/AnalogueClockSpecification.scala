package com.madgag.picoclock

import com.madgag.logic.protocol.holtek.ht1632c.Channel.ChipSelect
import com.madgag.logic.protocol.holtek.ht1632c.Channel.ChipSelect.{Follower, Leader}
import com.madgag.logic.protocol.holtek.ht1632c.{ChipLed, LedAddress}

import scala.collection.immutable.SortedMap

object AnalogueClockSpecification {
  val chipBitfieldSize: SortedMap[ChipSelect, Int] = SortedMap(Leader -> 236, Follower.One -> 256)
  val baseOffsetByChip: SortedMap[ChipSelect, Int] = {//  chipByBaseOffset.map(_.swap) {

    val honky: Seq[Int] = (0 +: chipBitfieldSize.values.toSeq).tail
    val tuples = chipBitfieldSize.keys.toSeq.zip(honky.scanLeft(0)(_ + _))
    SortedMap.from(tuples)
  }
  val chipByBaseOffset: SortedMap[Int, ChipSelect] = baseOffsetByChip.map(_.swap)

  def ledAddressFrom(ledOffsetWithinChip: Int): LedAddress =
    LedAddress(ledOffsetWithinChip / 4, 3 - (ledOffsetWithinChip % 4))

  def ledOffsetWithinChipFrom(ledAddress: LedAddress): Int =
    (ledAddress.memoryAddress * 4) + (3 - ledAddress.dataIndex)

  def chipLedFrom(ledId: Int): Option[ChipLed] = chipByBaseOffset.rangeTo(ledId).lastOption.map { (base, cs) =>
    ChipLed(cs, ledAddressFrom(ledOffsetWithinChip = ledId - base))
  }

  def ledIdFrom(chipLed: ChipLed): Int =
    ledOffsetWithinChipFrom(chipLed.ledAddress) + baseOffsetByChip(chipLed.chipSelect)

}
