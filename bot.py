import discord
from discord import channel
import requests
from discord.ext import tasks
import json

client = discord.Client()

vtubers = json.load(open("vtuber.json"))

# Insert bot token here
bot_token = ''


def convertTime(raw) -> str:
    hour = int(raw[11:13])
    month = int(raw[5:7])
    day = int(raw[8:10])
    year = int(raw[:4])

    hour += 9

    if hour >= 24:
        hour -= 24
        day += 1
        if day > 29 and month == 2 and year % 4 == 0:
            day -= 29
            month += 1
        elif day > 28 and month == 2:
            day -= 28
            month += 1
        elif day > 31 and (month <= 7 and month % 2 == 1 or month >= 8 and month % 2 == 0):
            day -= 31
            month += 1
        elif day > 30 and (month <= 7 and month % 2 == 0 or month >= 8 and month % 2 == 1):
            day -= 30
            month += 1

        if month > 12:
            month -= 12

    def convertToDigits(num) -> str:
        if num < 10:
            return '0' + str(num)
        return str(num)

    def convertMonth(num) -> str:
        if num == 1:
            return "January"
        if num == 2:
            return "February"
        if num == 3:
            return "March"
        if num == 4:
            return "April"
        if num == 5:
            return "May"
        if num == 6:
            return "June"
        if num == 7:
            return "July"
        if num == 8:
            return "August"
        if num == 9:
            return "September"
        if num == 10:
            return "October"
        if num == 11:
            return "November"
        if num == 12:
            return "December"

    hour = convertToDigits(hour)
    month = convertMonth(month)
    day = convertToDigits(day)

    return hour + raw[13:16] + ' (JST) on ' + day + " " + month


async def updateData(index) -> None:
    cur_vtuber = vtubers[index]
    # ------ HoloAPI -------
    url = "https://holodex.net/api/v2/channels/" + \
        cur_vtuber["youtube_channel_id"] + "/videos"
    url_collab = "https://holodex.net/api/v2/channels/" + \
        cur_vtuber["youtube_channel_id"] + "/collabs"
    querystring = {"include": "live_info"}

    headers = {'Content-Type': 'application/json'}
    # ----------------------
    disc_ids = cur_vtuber["disc_channel_id"]
    disc_channel = []
    disc_amount = len(disc_ids)

    for i in range(disc_amount):
        disc_channel.append(client.get_channel(disc_ids[i]))

    response = requests.request(
        "GET", url, headers=headers, params=querystring)

    new_arr = response.json()
    new_data = {"live": [], "upcoming": [], "ended": []}

    channel_info = new_arr[0]["channel"]
    if "english_name" in channel_info:
        streamer_name = channel_info["english_name"]
    else:
        streamer_name = channel_info["name"]
    end_stream_count = 0

    # Splitting the data
    for data in new_arr:
        data_status = data['status']
        if data_status == "upcoming":
            new_data["upcoming"].append(data)
        elif data_status == "live":
            new_data["live"].append(data)
        elif data_status == "past" or data_status == "missing" and end_stream_count < 5:
            end_stream_count += 1
            new_data["ended"].append(data)

    dict_data = cur_vtuber["dict_data"]
    for new_upcoming in new_data["upcoming"]:
        has_found = False
        for old_upcoming in dict_data["upcoming"]:
            if new_upcoming["id"] == old_upcoming["id"]:
                if new_upcoming["start_scheduled"] != old_upcoming["start_scheduled"]:
                    time = convertTime(new_upcoming["start_scheduled"])
                    for i in range(disc_amount):
                        await disc_channel[i].send(streamer_name + " rescheduled the upcoming stream to " + time + "\n" + "https://www.youtube.com/watch?v=" + str(new_upcoming["id"]))
                has_found = True
                break
        if not has_found:
            time = convertTime(new_upcoming["start_scheduled"])
            for i in range(disc_amount):
                await disc_channel[i].send(streamer_name + " is going to stream at " + time + "\n" + "https://www.youtube.com/watch?v=" + str(new_upcoming["id"]))
    dict_data["upcoming"] = new_data["upcoming"]

    for new_live in new_data["live"]:
        has_found = False
        for old_live in dict_data["live"]:
            if new_live["id"] == old_live["id"]:
                has_found = True
                break
        if not has_found:
            for i in range(disc_amount):
                await disc_channel[i].send(streamer_name + " is now live!" + "\n" + "https://www.youtube.com/watch?v=" + str(new_live["id"]))

    for new_ended in new_data["ended"]:
        for old_live in dict_data["live"]:
            if new_ended["id"] == old_live["id"]:
                for i in range(disc_amount):
                    await disc_channel[i].send(streamer_name + "'s stream has ended.")
                break
    dict_data["live"] = new_data["live"]

    # ----Collab-----
    response_collab = requests.request(
        "GET", url_collab, headers=headers, params=querystring)

    new_arr = response_collab.json()
    new_data = {"live": [], "upcoming": [], "ended": []}

    # Splitting the data
    for data in new_arr:
        data_status = data['status']
        if data_status == "upcoming":
            new_data["upcoming"].append(data)
        elif data_status == "live":
            new_data["live"].append(data)
        elif data_status == "past" or data_status == "missing":
            new_data["ended"].append(data)

    col_data = cur_vtuber["col_data"]

    for new_upcoming in new_data["upcoming"]:
        if "english_name" in new_upcoming["channel"].keys():
            collab_streamer_name = new_upcoming["channel"]["english_name"]
            has_found = False
            for old_upcoming in col_data["upcoming"]:
                if new_upcoming["id"] == old_upcoming["id"]:
                    if new_upcoming["start_scheduled"] != old_upcoming["start_scheduled"]:
                        time = convertTime(new_upcoming["start_scheduled"])
                        for i in range(disc_amount):
                            await disc_channel[i].send(streamer_name + " rescheduled the upcoming collab stream with " + collab_streamer_name +
                                                       " to " + time + "\n" + "https://www.youtube.com/watch?v=" + str(new_upcoming["id"]))
                    has_found = True
                    break
            if not has_found:
                time = convertTime(new_upcoming["start_scheduled"])
                for i in range(disc_amount):
                    await disc_channel[i].send(streamer_name + " is going to have collab stream with " + collab_streamer_name + " at " + time + "\n"
                                               + "https://www.youtube.com/watch?v=" + str(new_upcoming["id"]))
        else:
            collab_streamer_name = new_upcoming["channel"]["name"]
            has_found = False
            for old_upcoming in col_data["upcoming"]:
                if new_upcoming["id"] == old_upcoming["id"]:
                    if new_upcoming["start_scheduled"] != old_upcoming["start_scheduled"]:
                        time = convertTime(new_upcoming["start_scheduled"])
                        for i in range(disc_amount):
                            await disc_channel[i].send(streamer_name + " rescheduled the upcoming collab stream with " + collab_streamer_name +
                                                       " to " + time + "\n" + "https://www.youtube.com/watch?v=" + str(new_upcoming["id"]))
                    has_found = True
                    break
            if not has_found:
                time = convertTime(new_upcoming["start_scheduled"])
                for i in range(disc_amount):
                    await disc_channel[i].send(streamer_name + " is going to have collab stream with " + collab_streamer_name + " at " + time + "\n"
                                               + "https://www.youtube.com/watch?v=" + str(new_upcoming["id"]))
    col_data["upcoming"] = new_data["upcoming"]

    for new_live in new_data["live"]:
        if "english_name" in new_live["channel"].keys():
            collab_streamer_name = new_live["channel"]["english_name"]
            has_found = False
            for old_live in col_data["live"]:
                if new_live["id"] == old_live["id"]:
                    has_found = True
                    break
            if not has_found:
                for i in range(disc_amount):
                    await disc_channel[i].send(streamer_name + "'s collab with " + collab_streamer_name + " is now live!" + "\n"
                                               + "https://www.youtube.com/watch?v=" + str(new_live["id"]))
        else:
            collab_streamer_name = new_live["channel"]["name"]
            has_found = False
            for old_live in col_data["live"]:
                if new_live["id"] == old_live["id"]:
                    has_found = True
                    break
            if not has_found:
                for i in range(disc_amount):
                    await disc_channel[i].send(streamer_name + "'s collab with " + collab_streamer_name + " is now live!" + "\n"
                                               + "https://www.youtube.com/watch?v=" + str(new_live["id"]))

    for new_ended in new_data["ended"]:
        if "english_name" in new_ended["channel"].keys():
            collab_streamer_name = new_ended["channel"]["english_name"]
            for old_live in col_data["live"]:
                if new_ended["id"] == old_live["id"]:
                    for i in range(disc_amount):
                        await disc_channel[i].send(streamer_name + "'s collab stream with " + collab_streamer_name + " has ended.")
                    break
        else:
            collab_streamer_name = new_ended["channel"]["name"]
            for old_live in col_data["live"]:
                if new_ended["id"] == old_live["id"]:
                    for i in range(disc_amount):
                        await disc_channel[i].send(streamer_name + "'s collab stream with " + collab_streamer_name + " has ended.")
                    break
    col_data["live"] = new_data["live"]


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@tasks.loop(seconds=60)
async def check_schedule():
    for i in range(len(vtubers)):
        await updateData(i)
    print("Finished updating")


@check_schedule.before_loop
async def before_my_task():
    await client.wait_until_ready()

check_schedule.start()


client.run(bot_token)
