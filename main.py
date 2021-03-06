import requests
from datetime import datetime
from datetime import timedelta
import pytz
import boto3
import humanize

#Alex Dobrovansky
#27 Feb 18

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, outputType, reprompt_text, should_end_session):
    if outputType == "SSML":
        return {
            'outputSpeech': {
                'type': outputType,
                outputType: output
            },
            'card': {
                'type': 'Simple',
                'title': title,
                'content': output
            },
            'reprompt': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': reprompt_text
                }
            },
            'shouldEndSession': should_end_session
        }
    else:
        return {
            'outputSpeech': {
                'type': 'PlainText',
                'text': output
            },
            'card': {
                'type': 'Simple',
                'title': title,
                'content': output
            },
            'reprompt': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': reprompt_text
                }
            },
            'shouldEndSession': should_end_session
        }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }




#Actual logic code

def secondsTilBus(busTime,timeZone):
    return (busTime - datetime.now(timeZone)).seconds
    

def time2Response(first, firstLine, firstMode, second, secondLine, secondMode):
    result = "The next " + firstLine + " " + firstMode + " will arrive in "
    result += humanize.naturaldelta(first)
    if (firstLine == secondLine):
        result += ". The " + secondMode + " after that will arrive in "      
    else:
        result += ". The " + secondLine + " " + secondMode + " will arrive in "
    result += humanize.naturaldelta(second)
    result += "."

    return result


def getBusInfo(userId):
    
    table = boto3.resource('dynamodb').Table('busDB')
    try:
        resp = table.get_item(Key={'userID':userId})                    
        base = "https://api.navitia.io/v1/"
        stopArea = resp['Item']['stop_area'] 
        line = resp['Item']['line'] #"WHT:4-Whistler"
        region = resp['Item']['region']
        
        if (line == "ALL"):
            url = base + "coverage/" + region + "/stop_areas/" + stopArea + "/departures?count=6"
        else:
            url = base + "coverage/" + region + "/stop_areas/" + stopArea + "/lines/" + line + "/departures?count=3"
        print(url)
        r = requests.get(url,auth=('INSERT API KEY HERE',''))
        print(r)
        
        bus0 = r.json()["departures"][0]["stop_date_time"]["departure_date_time"]
        bus0Line = r.json()["departures"][0]["route"]["line"]["name"]
        bus0Mode = r.json()["departures"][0]["display_informations"]["commercial_mode"]
        bus1 = r.json()["departures"][1]["stop_date_time"]["departure_date_time"]
        bus1Line = r.json()["departures"][1]["route"]["line"]["name"]
        bus1Mode = r.json()["departures"][1]["display_informations"]["commercial_mode"]
        if (bus1 == bus0) and (bus0Line == bus1Line):
            bus1 = r.json()["departures"][2]["stop_date_time"]["departure_date_time"]
            bus1Line = r.json()["departures"][2]["route"]["line"]["name"]
            bus1Mode = r.json()["departures"][2]["display_informations"]["commercial_mode"]
        
        TZ = pytz.timezone(r.json()["context"]["timezone"])
        bus0Time = TZ.localize(datetime.strptime(bus0, '%Y%m%dT%H%M%S'))
        bus0Seconds = secondsTilBus(bus0Time, TZ)
        bus1Time = TZ.localize(datetime.strptime(bus1, '%Y%m%dT%H%M%S'))
        bus1Seconds = secondsTilBus(bus1Time, TZ)
        return time2Response(bus0Seconds,bus0Line,bus0Mode,bus1Seconds,bus1Line,bus1Mode)
    except KeyError:
        return "Error: You have not selected a stop"
    


def sameResponseForEverything(userId):
    session_attributes = {}
    speech_output = getBusInfo(userId)
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response("Tram Trackr", speech_output, "Simple", None, should_end_session))



def getUserId(userId):
    session_attributes = {}
    print(userId)
    speech_output = '<speak>Your User ID is <say-as interpret-as="spell-out">' + userId + "</say-as></speak>"
    print(speech_output)
    should_end_session = True
    return build_response(session_attributes,build_speechlet_response(userId, speech_output, "SSML", None, should_end_session))

def setStopId(userId,intent):
    session_attributes = {}
    if ('stopId' in intent['slots']):
        stopId = str(intent['slots']['stopId']['value'])
        table = boto3.resource('dynamodb').Table('busDB')
        resp = table.get_item(Key={'userID':stopId})
        if 'Item' in resp:
            stopArea = resp['Item']['stop_area']
            line = resp['Item']['line']
            region = resp['Item']['region']
            #new item 
            table.put_item(
                Item={
                    'userID':userId,
                    'stop_area':stopArea,
                    'line':line,
                    'region':region
                })
            #delete old item
            table.delete_item(Key={'userID':stopId})

            speech_output = "Stop ID has been updated"
            return build_response(session_attributes,build_speechlet_response(speech_output,speech_output,"Simple",None,True))        
        else:
            speech_output = "Could not find that stop ID"
            return build_response(session_attributes,build_speechlet_response(speech_output,speech_output,"Simple","Please say a stop id",False))        
    else:
        speech_output = "Please give me your stop ID"
        return build_response(session_attributes,build_speechlet_response(speech_output,speech_output,"Simple","Please say a stop id",False))
    
        

def get_welcome_response():
    session_attributes = {}
    speech_output = "Hello!"
    should_end_session = True
    return build_response(session_attributes,build_speechlet_response("Welcome", speech_output, "Simple", None, should_end_session))

#stuff for alexa (that I need to edit)

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'] + ", userId=" + session['user']['userId'])
    # Dispatch to your skill's launch


    return sameResponseForEverything(session['user']['userId'])


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'] + ", userId="+session['user']['userId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    elif intent_name == "getUserId":
        return getUserId(session['user']['userId'])
    elif intent_name == "setStopId":
        return setStopId(session['user']['userId'],intent)
    else:
        return sameResponseForEverything(session['user']['userId'])
        #raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here





#this is run when code is launched

def handler(event, context):
    print("event.session.application.applicationId=" + event['session']['application']['applicationId'])
    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

