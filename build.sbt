scalaVersion := "3.3.7"

Test / testOptions +=
  Tests.Argument(TestFrameworks.ScalaTest, "-u", s"test-results/scala-${scalaVersion.value}", "-o")

libraryDependencies ++= Seq(
  "com.madgag.logic-capture" %% "client" % "12.0.0",
  "com.madgag" %% "scala-collection-plus" % "1.0.0",
  "org.scalatest" %% "scalatest" % "3.2.19" % Test,
  "org.typelevel" %% "weaver-cats" % "0.11.3" % Test
) ++ Seq("kantan.csv", "kantan.csv-java8").map(artifactId => "io.github.kantan-scala" %% artifactId % "0.11.0")