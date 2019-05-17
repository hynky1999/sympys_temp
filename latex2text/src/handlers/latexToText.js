import latexToText from '../chrome/latexToText'
import path from "path"
import qs from "querystring"
import base64 from "base-64";

export const handler = async (event, context, callback) => {
    console.log("Event received:"+JSON.stringify(event, null, 2))
    let {body} = event;
    console.log("Http payload:"+body)
    if(event.isBase64Encoded) {
        body = base64.decode(body)
        console.log("Decoded http payload:"+body)
    }
    body = body && qs.parse(body) || ""
    const url =`https://edureact-dev.s3.amazonaws.com/mathlive-index.html`;
    const {
    latexData = ""
    } = body    

    let data = {}

    console.log("Latex data to process", latexData)

    const startTime = Date.now()
    if(latexData === "") {
        return callback(null, {
            statusCode: 400,
            body: JSON.stringify({message : "Bad request"}),
            headers: {
                "Content-Type": "application/json",
            },
        })
    }
    try {
        data = await latexToText(url, latexData)
    } catch (error) {
        console.error("Error processing latex data for", url, error)
        return callback(error)
    }
    console.log(`Job done: Took ${Date.now() - startTime}ms to process`)

    return callback(null, {
        statusCode: 200,
        body: JSON.stringify(data),
        headers: {
            "Content-Type": "application/json",
        },
    })
}

export default handler
