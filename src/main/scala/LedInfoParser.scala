import kantan.csv.*
import kantan.csv.ops.*
import com.madgag.scala.collection.decorators._

import java.io.*

case class Coord(x: Int, y: Int) {
  val r = math.sqrt(math.pow(x ,2) + math.pow(y ,2))
  val angle: Option[Double] = Option.when(r > 0)(Math.atan2(x, -y))
  val sector: Option[Int] = angle.map(a => Math.floorMod(math.round(60 * a / Math.TAU).toInt, 60))
}

case class LedInfo(id: Int, coord: Coord, size: Int)

given RowDecoder[LedInfo] = {
  RowDecoder.decoder[Int, Int, Int, Int, LedInfo](0, 1, 2, 3) {
    (id, x, y, size) => LedInfo(id, Coord(x,y), size)
  }
}

@main def hello() = {
  val boom = new File("led_coordinates.csv").asUnsafeCsvReader[LedInfo](rfc.withHeader)
  val leds: Seq[LedInfo] = boom.toList
  println(leds.groupUp(_.coord.sector)(_.sortBy(_.coord.r).map(_.id).mkString("[", ",", "],")).toList.sortBy(_._1).map(_._2).mkString("\n"))
}