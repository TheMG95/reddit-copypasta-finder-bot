import praw
import praw.models
import praw.exceptions
import threading
import string
import os


def create_reply(**kwargs):
    reply = string.Template(reply_template).substitute(**kwargs)
    return reply


def find_copypasta(comment: praw.models.Comment):
    global replies_to_send
    if comment.author == bot_user:
        return

    query: str = comment.body.lower().replace("u/copypastafinderbot", "").strip()

    result: list = list(copypasta_sub.search(query, limit=1))

    if not result or not query:
        reply = string.Template(not_found_template).substitute(query=query)
        if len(reply) > 10_000:
            reply = string.Template(not_found_template).substitute(query="_Too long to display_")

        replies_to_send.append({
            "reply": reply,
            "comment": comment,
            "time": comment.created_utc
        })

        return

    result: praw.models.Submission = result[0]

    reply = create_reply(
        title=result.title,
        nsfw=(" **[NSFW]**" if result.over_18 else ""),
        spoiler=(" **[SPOILER]**" if result.spoiler else ""),
        url=result.shortlink,
        body=result.selftext,
    )

    if len(reply) > 10_000:
        too_long_phrase = " _(Too long to display all)_"
        difference = len(reply) - 10_000 + len(too_long_phrase)

        reply = create_reply(
            title=result.title,
            nsfw=(" **[NSFW]**" if result.over_18 else ""),
            spoiler=(" **[SPOILER]**" if result.spoiler else ""),
            url=result.shortlink,
            body=result.selftext[:-difference] + too_long_phrase,
        )

    replies_to_send.append({
        "reply": reply,
        "comment": comment,
        "time": comment.created_utc
    })


def main():
    global replies_to_send
    mentions = list(reddit.inbox.mentions(limit=10))

    comment: praw.models.Comment

    threads: list = []
    for comment in mentions:
        if type(comment) != praw.models.Comment:
            continue
        if comment.id == last_replied:
            print("done")
            break

        thread = threading.Thread(target=find_copypasta, args=(comment,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    replies_to_send = sorted(replies_to_send, key=lambda d: d["time"], reverse=True)

    print(f"Sending {len(replies_to_send)}")
    for reply in replies_to_send:
        reply["comment"].reply(reply["reply"])

    # reply_storage.update_one({"_id": 0}, {"$set": {"last_replied": mentions[0].id}})


if __name__ == '__main__':
    # Define global variables

    reddit = praw.Reddit(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        password=os.getenv("PASSWORD"),
        user_agent="CopypastaFinderBot",
        username=os.getenv("USERNAME")
    )
    bot_user: praw.models.User = reddit.user.me()

    copypasta_sub = reddit.subreddit("copypasta")

    with open("reply_template.txt") as f:
        reply_template = f.read()

    with open("not_found_template.txt") as f:
        not_found_template = f.read()

    last_replied: str = list(bot_user.comments.new(limit=1))[0].parent_id.removeprefix("t1_")
    replies_to_send: list = []

    main()
