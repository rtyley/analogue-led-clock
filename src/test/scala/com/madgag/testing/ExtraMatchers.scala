package com.madgag.testing

import cats.Show
import cats.syntax.show.*
import org.scalactic.Prettifier
import org.scalatest.matchers.{MatchResult, Matcher}
import spire.algebra.MetricSpace.distance
import spire.algebra.{MetricSpace, Order}
import spire.syntax.all.*

import java.time.Duration
import java.time.temporal.ChronoUnit.MICROS
import scala.reflect.ClassTag

trait TargetZone[T] {
  def matchResultGiven(actual: T): MatchResult
}


def fallWithin[T](spread: TargetZone[T]): Matcher[T] = new Matcher[T] {
  def apply(actual: T): MatchResult = spread.matchResultGiven(actual)

  override def toString: String = "fall within (" + Prettifier.default(spread) + ")"
}

extension [V: {Show, ClassTag}](target: V)
  infix def ±[R: {Show, Order}](tolerance: R)(using MetricSpace[V, R]): TargetZone[V] = {
    val tolDesc = s"the tolerance of ${tolerance.show}"

    (actual: V) => {
      val d = distance(actual, target)
      val diffDesc = s"${actual.show} was ${d.show} away from ${target.show}, which"

      MatchResult(d <= tolerance, s"$diffDesc exceeds $tolDesc", s"$diffDesc is within $tolDesc")
    }
  }

extension (d: Int)
  def μs: Duration = Duration.of(d, MICROS)