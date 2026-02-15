package com.madgag.picoclock

import cats.effect.*
import weaver.IOSuite

object FooTest extends IOSuite {
  type Res = Int

  def sharedResource: Resource[IO, Res] = Resource.pure(234)
  
  test("be able to do what is required") { (thing, log) =>
    for {
      _ <- log.info(s"Hi there!")
    } yield expect(clue(thing) == 234)
  }
}
