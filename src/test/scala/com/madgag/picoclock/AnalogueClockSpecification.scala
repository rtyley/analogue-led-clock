package com.madgag.picoclock

import com.madgag.logic.protocol.holtek.ht1632c.Channel.ChipSelect
import com.madgag.logic.protocol.holtek.ht1632c.Channel.ChipSelect.{Follower, Leader}
import com.madgag.logic.protocol.holtek.ht1632c.{ChipLed, LedAddress}
import com.madgag.scala.collection.decorators.*

import scala.collection.immutable.SortedMap

case class DisplayTime(hour: Int, minute: Int) {
  require(hour >=0 && hour < 12)
  require(minute >=0 && minute < 60)
}

object AnalogueClockSpecification {
  val chipBitfieldSize: SortedMap[ChipSelect, Int] = SortedMap(Leader -> 236, Follower.One -> 256)
  val baseOffsetByChip: SortedMap[ChipSelect, Int] =
    SortedMap.from(chipBitfieldSize.keys.toSeq.zip((0 +: chipBitfieldSize.values.toSeq).tail.scanLeft(0)(_ + _)))

  val chipByBaseOffset: SortedMap[Int, ChipSelect] = baseOffsetByChip.map(_.swap)

  def ledAddressFrom(ledOffsetWithinChip: Int): LedAddress =
    LedAddress(ledOffsetWithinChip / 4, 3 - (ledOffsetWithinChip % 4))

  def ledOffsetWithinChipFrom(ledAddress: LedAddress): Int =
    (ledAddress.memoryAddress * 4) + (3 - ledAddress.dataIndex)

  def chipLedFrom(ledId: Int): ChipLed = chipByBaseOffset.rangeTo(ledId).last match {
    case (base, cs) => ChipLed(cs, ledAddressFrom(ledOffsetWithinChip = ledId - base))
  }

  def ledIdFrom(chipLed: ChipLed): Int =
    ledOffsetWithinChipFrom(chipLed.ledAddress) + baseOffsetByChip(chipLed.chipSelect)

  val centerLed: ChipLed = chipLedFrom(233)

  val handLeds: Seq[Seq[ChipLed]] = Seq(
    Seq(244,242,241,240,239,238,237,236),
    Seq(245,258,257,256,255,254,253,252),
    Seq(259,274,273,272,271,270,269,268),
    Seq(260,290,289,288,287,286,285,284),
    Seq(261,306,305,304,303,302,301,300),
    Seq(275,322,321,320,319,318,317,316),
    Seq(276,338,337,336,335,334,333,332),
    Seq(277,354,353,352,351,350,349,348),
    Seq(291,370,369,368,367,366,365,364),
    Seq(292,386,385,384,383,382,381,380),
    Seq(293,402,401,400,399,398,397,396),
    Seq(307,418,417,416,415,414,413,412),
    Seq(308,434,433,432,431,430,429,428),
    Seq(309,450,449,448,447,446,445,444),
    Seq(323,466,465,464,463,462,461,460),
    Seq(324,482,481,480,479,478,477,476),
    Seq(325,6,5,4,3,2,1,0),
    Seq(339,22,21,20,19,18,17,16),
    Seq(340,38,37,36,35,34,33,32),
    Seq(341,54,53,52,51,50,49,48),
    Seq(355,70,69,68,67,66,65,64),
    Seq(356,86,85,84,83,82,81,80),
    Seq(357,102,101,100,99,98,97,96),
    Seq(371,118,117,116,115,114,113,112),
    Seq(372,134,133,132,131,130,129,128),
    Seq(373,150,149,148,147,146,145,144),
    Seq(387,166,165,164,163,162,161,160),
    Seq(388,182,181,180,179,178,177,176),
    Seq(389,198,197,196,195,194,193,192),
    Seq(403,214,213,212,211,210,209,208),
    Seq(404,71,223,222,221,220,219,218),
    Seq(405,87,207,206,205,204,203,202),
    Seq(419,103,191,190,189,188,187,186),
    Seq(420,119,175,174,173,172,171,170),
    Seq(421,135,159,158,157,156,155,154),
    Seq(435,151,143,142,141,140,139,138),
    Seq(436,167,127,126,125,124,123,122),
    Seq(437,183,111,110,109,108,107,106),
    Seq(451,199,95,94,93,92,91,90),
    Seq(452,215,79,78,77,76,75,74),
    Seq(453,72,63,62,61,60,59,58),
    Seq(467,88,47,46,45,44,43,42),
    Seq(468,104,31,30,29,28,27,26),
    Seq(469,120,15,14,13,12,11,10),
    Seq(483,136,491,490,489,488,487,486),
    Seq(484,152,475,474,473,472,471,470),
    Seq(485,168,459,458,457,456,455,454),
    Seq(7,184,443,442,441,440,439,438),
    Seq(8,200,427,426,425,424,423,422),
    Seq(9,216,411,410,409,408,407,406),
    Seq(23,73,395,394,393,392,391,390),
    Seq(24,89,379,378,377,376,375,374),
    Seq(25,105,363,362,361,360,359,358),
    Seq(39,121,347,346,345,344,343,342),
    Seq(40,137,331,330,329,328,327,326),
    Seq(41,153,315,314,313,312,311,310),
    Seq(55,169,299,298,297,296,295,294),
    Seq(56,185,283,282,281,280,279,278),
    Seq(57,201,267,266,265,264,263,262),
    Seq(243,217,251,250,249,248,247,246)
  ).map(_.map(chipLedFrom))

  val hourMarkerLeds: Seq[ChipLed] = handLeds.grouped(5).map(_.head.last).toSeq

  val baseDisplayLeds: Set[ChipLed] = (hourMarkerLeds :+ centerLed).toSet

  val hourHandLength = 5

  def ledsFor(hour: Int, minute: Int): Set[ChipLed] =
    baseDisplayLeds ++ handLeds(math.round((((hour % 12) * 60) + minute) / 12f)).take(hourHandLength) ++ handLeds(minute)

  def handsFor(chipLeds: Set[ChipLed]): Map[Int, Set[ChipLed]] =
    (chipLeds -- baseDisplayLeds).groupBy(cl => handLeds.indexWhere(_.contains(cl)))

  def displayTimeFor(chipLeds: Set[ChipLed]): Option[DisplayTime] = {
    val hands: Map[Int, Int] = handsFor(chipLeds).mapV(_.size)
    for {
      hourHand <- hands.find(_._2 >= hourHandLength).minByOption(_._2).map(_._1)
      minute <- hands.find(_._2 >= 7).map(_._1) if hands.keySet == Set(hourHand, minute)
    } yield DisplayTime(hourHand / 12, minute)
  }
}
