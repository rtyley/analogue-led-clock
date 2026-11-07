scalaVersion := "3.9.0"

libraryDependencies ++= Seq(
  "com.madgag.logic-capture" %% "client" % "14.0.1",
  "com.madgag" %% "scala-collection-plus" % "1.0.0",
  "org.scalatest" %% "scalatest" % "3.2.20" % Test,
  "org.typelevel" %% "weaver-cats" % "0.13.1" % Test
) ++ Seq("kantan.csv", "kantan.csv-java8").map(artifactId => "io.github.kantan-scala" %% artifactId % "0.11.0")
