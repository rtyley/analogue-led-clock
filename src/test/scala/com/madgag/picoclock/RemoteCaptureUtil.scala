package com.madgag.picoclock

import com.madgag.micropython.logiccapture.aws.{AWS, AWSIO}
import com.madgag.micropython.logiccapture.client.RemoteCaptureClient
import com.madgag.micropython.logiccapture.model.{GitSource, GitSpec}
import software.amazon.awssdk.services.sfn.SfnAsyncClient
import software.amazon.awssdk.services.sfn.model.SfnRequest

object RemoteCaptureUtil {

  val deviceFS: os.SubPath = "pico-clock/device-fs"
  
  val githubToken: String = sys.env("LOGIC_CAPTURE_REPO_CLONE_GITHUB_TOKEN")

  val aws = new AWS(profile = "logic-capture-client")

  val remoteCaptureClient = new RemoteCaptureClient(
    awsIo = new AWSIO[SfnAsyncClient, SfnRequest](aws.SFN),
    stateMachineArn = s"arn:aws:states:${AWS.region.id}:${AWS.awsAccountId}:stateMachine:pico-logic-capture"
  )
  
  val gitSource = GitSource(githubToken, GitSpec.forPathInThisRepo(deviceFS))
}
