import latexToText from '../chrome/latexToText'
import path from "path"

export const handler = async (event, context, callback) => {
    const queryStringParameters = event.queryStringParameters || {}
    const url = `file:///${path.resolve("../html/index.html")}`;
    console.log(url)
    const {
    latexData = ""
    } = queryStringParameters

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
