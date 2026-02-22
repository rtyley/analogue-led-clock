package com.madgag.picoclock;

import com.madgag.logic.protocol.holtek.ht1632c.Channel.ChipSelect.Leader
import com.madgag.logic.protocol.holtek.ht1632c.{ChipLed, LedAddress}
import com.madgag.picoclock.AnalogueClockSpecification.{chipLedFrom, ledIdFrom}
import org.scalatest.{Inspectors, OptionValues}
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should

class AnalogueClockSpecificationTest extends AnyFlatSpec with should.Matchers with OptionValues with Inspectors {
    "LED ids and ChipLed" should "round trip" in {
        val allLedIds: Seq[Int] = 0 to 491
        forAll (allLedIds) { ledId =>
            val chipLed: ChipLed = chipLedFrom(ledId).value
            ledIdFrom(chipLed) shouldBe ledId
        }
    }

    it should "give specific LED ids" in {
        chipLedFrom(0).value shouldBe ChipLed(Leader, LedAddress(0, 3))
        chipLedFrom(1).value shouldBe ChipLed(Leader, LedAddress(0, 2))
        chipLedFrom(2).value shouldBe ChipLed(Leader, LedAddress(0, 1))
        chipLedFrom(3).value shouldBe ChipLed(Leader, LedAddress(0, 0))
        chipLedFrom(4).value shouldBe ChipLed(Leader, LedAddress(1, 3))
    }
}