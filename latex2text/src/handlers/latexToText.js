import latexToText from '../chrome/latexToText'
import path from "path"
import qs from "querystring"

export const handler = async (event, context, callback) => {
    const body = event.body && qs.parse(event.body) || ""
    const url = `file:///${path.resolve("./src/html/index.html")}`;
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
