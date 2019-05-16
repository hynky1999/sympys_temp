import CDP from 'chrome-remote-interface'
import sleep from '../utils/sleep'

export const latexToText = async (url, latexData) => {
  const LOAD_TIMEOUT = process.env.PAGE_LOAD_TIMEOUT || 1000 * 60

  let result = {}
  let loaded = false

  const loading = async (startTime = Date.now()) => {
    if (!loaded && Date.now() - startTime < LOAD_TIMEOUT) {
      await sleep(100)
      await loading(startTime)
    }
  }

  const [tab] = await CDP.List()
  const client = await CDP({ host: '127.0.0.1', target: tab })

  const {
    Network, Page, Runtime,
  } = client

  Network.requestWillBeSent((params) => {
    console.log('Chrome is sending request for:', params.request.url)
  })

  Page.loadEventFired(() => {
    loaded = true
  })
  try {
    await Promise.all([Network.enable(), Page.enable()])
    await Page.navigate({url})
    await Page.loadEventFired()
    await loading()
    result = await Runtime.evaluate({
      expression: `(
        () => ({ text : MathLive.latexToSpeakableText("${latexData}") })
      )();
      `,
      returnByValue: true,
    })
  } catch (error) {
    console.error(error)
  }

  await client.close()

  return result.result.value;
}
export default latexToText
