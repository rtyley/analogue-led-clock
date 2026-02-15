scalaVersion := "3.3.6"

Test / testOptions +=
  Tests.Argument(TestFrameworks.ScalaTest, "-u", s"test-results/scala-${scalaVersion.value}", "-o")

libraryDependencies ++= Seq(
  "com.madgag.logic-capture" %% "client" % "10.0.1",
  "org.scalatest" %% "scalatest" % "3.2.19" % Test,
  "org.typelevel" %% "weaver-cats" % "0.11.3" % Test
)