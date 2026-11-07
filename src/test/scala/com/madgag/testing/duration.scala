package com.madgag.testing

import cats.Show
import com.gu.time.duration.formatting.*
import spire.algebra.{MetricSpace, Order}

import java.time.Duration
import java.time.temporal.ChronoUnit.MICROS

object duration:

  given Show[Duration] = Show.show(_.format())

  given Order[Duration] = Order.fromComparable[Duration]

  given MetricSpace[Duration, Duration] with
    def distance(x: Duration, y: Duration): Duration = x.minus(y).abs()

  extension (d: Int)
    def μs: Duration = Duration.of(d, MICROS)

