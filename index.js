'use strict'

console.log('Loading function')
const doc = require('dynamodb-doc')
const dynamo = new doc.DynamoDB()
var lastId
var currentId
function randomIntInc (low, high) {
    return Math.floor(Math.random() * (high - low + 1) + low);
}

function sleep(ms){
    return new Promise(resolve=>{
        setTimeout(resolve,ms)
    })
}

function onScan(err,data){
    if (err){
        console.log("Unable to scan DB: busDBLastEntry. Error: ", JSON.stringify(err, null, 2))
    }else{
        
        lastId = data.Items[0].userID
        console.log("FUNCTIONRAN")
        console.log(lastId)
    }
}

// All the request info in event
// "handler" is defined on the function creation
exports.handler = (event, context, callback) => {
    
    // Callback to finish response
    const done = (err, res) => callback(null, {
        statusCode: err ? '400' : '200',
        body: err ? err.message : JSON.stringify(res),
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Headers':'Access-Control-Allow-Origin,Content-Type',
            'Access-Control-Allow-Origin':'*',
            //'Vary':'Origin'
        }
    })
    
    // To support mock testing, accept object not just strings
    if (typeof event.body == 'string')
        event.body = JSON.parse(event.body)
        console.log(event.httpMethod)
        console.log(event.body)
    switch (event.httpMethod) {
        // Table name and key are in payload
        //case 'DELETE':
            //dynamo.deleteItem(event.body, done)
            //break

            
        // No payload, just a query string param
        //case 'GET':
            //dynamo.scan({ TableName: event.queryStringParameters.TableName }, done)
            //break
        // Table name and key are in payload
        case 'POST':
            //get entry in busDBLastEntry
            
            dynamo.scan({ TableName: "busDBLastEntry" },function(err,data){
                if (err){
                    console.log("Unable to scan DB: busDBLastEntry. Error: ", JSON.stringify(err, null, 2))
                }else{
                    lastId = data.Items[0].userID
                }
                //id = busDBLastEntry[0]['ID'] + randomIntInc(1,9)
                console.log("LastId: ", lastId)
                
                if (parseInt(lastId) > 90){
                    lastId = "0"
                }
                var id = parseInt(lastId) + randomIntInc(1,9)
                console.log("id: ", id)
                //put in DB: id, line,stop_area
                var put = {"TableName":"busDB","Item":{"userID": id.toString(), "line":event.body.line,"stop_area":event.body.stop_area,"region":event.body.region}}
                var put1 = {"TableName":"busDBLastEntry","Item":{"userID": id.toString(), "line":event.body.line,"stop_area":event.body.stop_area,"region":event.body.region}}
                //return id
                console.log(put)
                var r = dynamo.deleteItem({TableName:"busDBLastEntry",Key:{userID: lastId.toString()}},function(err,data){if(err){console.log(err)}})
                console.log(r)
                dynamo.putItem(put1,function(err,data){if(err){console.log(err)}})
                dynamo.putItem(put,function(err,data){if(err){console.log(err)}})
                done(false,{"id":id})
                
            })
            break
           
        // Table name and key are in payload
        //case 'PUT':
            //dynamo.updateItem(event.body, done)
            //break
        case 'OPTIONS':
            done(false,"")
        default:
            done(new Error(`Unsupported method "${event.httpMethod}"`))
    }
}
