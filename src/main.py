import sys
import os
import boto3
from os.path import join, dirname
from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)
cardTableName = os.getenv("CARD_TABLE")
mediaTableName = os.getenv("MEDIA_TABLE")

client = boto3.resource(
    "dynamodb",
    region_name="us-west-2"
    # endpoint_url='http://localhost:8888'
)
cardTable = client.Table(cardTableName)
mediaTable = client.Table(mediaTableName)

app = FastAPI()

origins = [os.getenv("CORS_ORIGIN")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

handler = Mangum(app)


class Card(BaseModel):
    uuid: int
    title: str
    content: str
    subtitle: Optional[str] = ""
    icon: str
    ts: str
    comments: Optional[list] = ""
    medias: Optional[list] = ""
    tags: str


class Media(BaseModel):
    ts: str
    name: str
    path: str
    url: str
    type: str


@app.get("/")
def health_check():

    """ Get Health check """

    return {"statusCode": 200, "body": {"message": "OK"}}


# Cards handling -------------------------------------------------------


@app.get("/card/{uuid}")
async def get_card(uuid: int):

    """ Get card """

    if uuid:
        response = cardTable.query(KeyConditionExpression=Key("uuid").eq(uuid))
        return response["Items"]


@app.get("/cards")
async def get_cards():
    response = cardTable.scan()
    return response["Items"]


@app.get("/cards/{date_start}/{date_end}")
async def get_cards_between(date_start: str, date_end: str):

    """ Get all cards """

    # response = cardTable.scan()
    # return response["Items"]

    # response = cardTable.scan()

    # ds_y = date_start[0:4]
    # ds_m = date_start[4:6]
    # ds_d = date_start[6:8]
    # de_y = date_end[0:4]
    # de_m = date_end[4:6]
    # de_d = date_end[6:8]
    # ds = f"{ds_y}-{ds_m}-{ds_d}"
    # de = f"{de_y}-{de_m}-{de_d}"

    response = cardTable.query(
        # IndexName="date-index",
        # ProjectionExpression="#dt",
        # ExpressionAttributeNames={"#dt": "date"},
        KeyConditionExpression=Key("ts").between(date_start, date_end)
    )
    data = response["Items"]
    while "LastEvaluatedKey" in response:
        key = response["LastEvaluatedKey"]
        response = cardTable.query(ExclusiveStartKey=key)
        data.update(response["Items"])
    return data


@app.get("/cards/{date_range}")
async def get_cards_by_range(date_range: str):

    """ Get cards in range """

    if date_range:
        scan_kwargs = {
            "FilterExpression": Key("ts").between(*date_range)
            # 'ProjectionExpression': "#dt, name, type, path",
            # 'ExpressionAttributeNames': {"#dt": "date"}
        }

        done = False
        start_key = None

        while not done:
            if start_key:
                scan_kwargs["ExclusiveStartKey"] = start_key
            response = cardTable.scan(**scan_kwargs)
            cards = response.get("Items", [])

            for card in cards:
                print(f"\n{card['ts']} : {card['title']}")
                print(card["subtitle"])

            start_key = response.get("LastEvaluatedKey", None)
            done = start_key is None


@app.post("/card")
async def create_card(card: Card):

    """ Create a new card """

    cardObject = {}
    cardObject["uuid"] = card.uuid
    cardObject["ts"] = card.ts
    cardObject["icon"] = card.icon
    cardObject["title"] = card.title
    cardObject["subtitle"] = card.subtitle
    cardObject["content"] = card.content
    cardObject["comments"] = card.comments
    cardObject["medias"] = card.medias
    cardObject["tags"] = card.tags

    # if object is less than 400Kb (max record size supported by DynamoDB)
    if object_size_ok(cardObject):
        response = cardTable.put_item(Item=cardObject)
        return response
    else:
        print(
            "Object %s is more than 400Kb, record cannot be processed",
            cardObject,
        )


@app.put("/card")
async def update_card(card: Card):

    """ Modify a card """

    # if object is less than 400Kb (max record size supported by DynamoDB)
    if object_size_ok(card):
        response = cardTable.update_item(
            Key={"uuid": card.uuid, "ts": card.ts},
            UpdateExpression="SET title = :title, subtitle = :subtitle, icon = :icon, content = :content",
            ExpressionAttributeValues={
                ":title": card.title,
                ":subtitle": card.subtitle,
                ":icon": card.icon,
                ":content": card.content,
            },
        )
        return response
    else:
        print("Object %s is more than 400Kb, record cannot be processed", card)


@app.delete("/card")
async def delete_card(card: Card):

    """ Delete a card """

    response = cardTable.delete_item(Key={"uuid": card.uuid, "ts": card.ts})
    return response


# Medias handling -----------------------------------------------------


@app.get("/media")
async def get_media_pages(filter_key="ts", filter_value="2020"):

    """ Get all medias (pages) """

    if filter_key and filter_value:
        filtering_exp = Key(filter_key).lt(filter_value)
        response = mediaTable.scan(FilterExpression=filtering_exp)
    else:
        response = mediaTable.scan(Limit=10)

    items = response["Items"]
    while True:
        # print len(response['Items'])
        if response.get("LastEvaluatedKey"):
            response = mediaTable.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"], Limit=10
            )
            items += response["Items"]
        else:
            break

    return items


@app.get("/media/{date}")
async def get_media_from_date(date: int):

    """ Get medias from date (eg: 20200717 :: year, month, day)"""

    response = mediaTable.query(KeyConditionExpression=Key("ts").eq(date))
    return response["Items"]


@app.get("/media/type/{type}")
async def get_media_of_type(type: str):

    """ Get medias of type (eg: picture | movie)"""

    response = mediaTable.scan(FilterExpression=Attr("type").eq(type))
    return response["Items"]


@app.get("/media/{date_range}")
async def get_medias_of_date_range(date_range: str):

    """ Get medias of a date range (eg: 20190717-20200717 :: year, month, day) """

    date_start = date_range.split("-")[0]
    date_end = date_range.split("-")[1]
    response = mediaTable.query(
        # ProjectionExpression="#dt, name",
        # ExpressionAttributeNames={"#dt": "date"},
        KeyConditionExpression=Key("ts").between(date_start, date_end)
    )
    return response["Items"]


@app.post("/media")
async def create_media(media: Media):

    """ Create a media record """

    mediaObject = {}
    mediaObject["ts"] = media.ts
    mediaObject["name"] = media.name
    mediaObject["path"] = media.path
    mediaObject["url"] = media.url
    mediaObject["type"] = media.type

    # if object is less than 400Kb (max record size supported by DynamoDB)
    if object_size_ok(mediaObject):
        response = mediaTable.put_item(Item=mediaObject)
        return response
    else:
        print(
            "Object %s is more than 400Kb, record cannot be processed",
            mediaObject,
        )


@app.put("/media")
async def update_media(media: Media):

    """ Modify a media record """

    # if object is less than 400Kb (max record size supported by DynamoDB)
    if object_size_ok(media):
        response = mediaTable.update_item(
            Key={"ts": media.ts, "name": media.name},
            UpdateExpression="SET path = :path, url = :url",
            ExpressionAttributeValues={
                ":path": media.title,
                ":url": media.subtitle,
            },
        )
        return response
    else:
        print(
            "Object %s is more than 400Kb, record cannot be processed", media
        )


@app.delete("/media")
async def delete_media(media: Media):

    """ Delete a media record """

    response = mediaTable.delete_item(Key={"ts": media.ts, "name": media.name})
    return response


# the total data (item size) that ends up being saved in dynamodb table is = Acutal data * (number of indexes + 1)
# https://stackoverflow.com/questions/33768971/how-to-calculate-dynamodb-item-size-getting-validationerror-400kb-boto
#
def object_size_ok(obj):
    objSize = sys.getsizeof(obj)
    nIndexes = 0
    computedSize = objSize * (nIndexes + 1)

    if computedSize <= 400000:  # 400Kb
        return True
    else:
        return False
