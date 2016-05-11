def signal_handler(signal, frame):
    print('')
    try:
        global conn
        conn.commit()
        conn.close()
    except:
        pass
    print('Exiting!')
    os._exit(0)


def print_submission_info(my_r_submission):
    try:
        print("Submission Info:")
        print("Submission URL: %s" % my_r_submission.url)
        print("Submission Permalink: %s" % my_r_submission.permalink)
        print("Submission Title: %s" % my_r_submission.title)
        print("Submission Author: %s" % my_r_submission.author)
        print("Submission Created (UTC): %s" % "{:%c}".format(
            datetime.datetime.fromtimestamp(my_r_submission.created_utc)))
    except:
        pass


def print_video_info(my_yt_video_entry):
    try:
        print('Video Info:')
        print('Video ID: %s' % 
              my_yt_video_entry["items"][0]["id"])
        print('Video published on: %s ' % 
              my_yt_video_entry["items"][0]["snippet"]["publishedAt"])
        print('Video view count: %s' % 
               my_yt_video_entry["items"][0]["statistics"]["viewCount"])
        print('Video title: %s' % 
              my_yt_video_entry["items"][0]["snippet"]["title"])
        print('Video channel: %s' % 
              my_yt_video_entry["items"][0]["snippet"]["channelTitle"])
    except:
        pass


def print_info(my_r_submission, my_yt_video_entry):
    print_submission_info(my_r_submission)
    print_video_info(my_yt_video_entry)


def print_time():
    print('Time: %s' % time.strftime("%c"))


def print_error(my_message, my_r_submission, my_yt_video_entry):
    print("!!!! %s !!!!" % my_message)
    print_time()
    print_info(my_r_submission, my_yt_video_entry)
    print('')


def print_warning(my_message, my_r_submission, my_yt_video_entry):
    print("** %s **" % my_message)
    print_time()
    print_info(my_r_submission, my_yt_video_entry)
    print('')


def bot_sleep():
    global bot_last_sleep
    r_refresh_login()
    sleepfor = max(0.0, bot_sleepsec - (time.time() - bot_last_sleep))
    time.sleep(sleepfor)
    bot_last_sleep = time.time()


def get_bot_settings():
    try:
        execfile(bot_settings_file, globals())
        return True
    except:
        print_error('Syntax error in %s' % bot_settings_file)
        return False



def check_processed(my_r_submission_id):
    global c
    if my_r_submission_id in bot_already_processed:
        return True
    try:
        c.execute('SELECT submissionId FROM processed WHERE submissionId=?',
                  (my_r_submission_id,))
    except:
        print_warning('Database search failed')
        return False
    if c.fetchone() != None:
            return True
    else:
        return False


def set_processed(my_r_submission_id):
    global bot_already_processed
    global c
    global conn
    try:
        bot_already_processed.append(my_r_submission_id)
        c.execute('INSERT INTO processed VALUES (?)', 
                  (my_r_submission_id,))
        conn.commit()
    except:
        print_warning('Database insert failed.')


def check_valid_yt_hostname(my_r_submission_url):
    suburl = urlparse(my_r_submission_url)
    if not any(suburl.hostname in s for s in yt_hostnames):
        return False
    else:
        return True


def get_repost_count(my_yt_video_id, my_r_subredit):
    bot_sleep()
    try:
        searchres = list(r.search('url:"%s"' % str(my_yt_video_id),
                         subreddit=my_r_subredit))
        r_repost_count = len(list(searchres))
        if r_repost_count > 0:
            r_repost_count = r_repost_count - 1
    except:
        e = sys.exc_info()[0]
        r_repost_count = "err"
        print_warning('Repost Search failed %s' % str(e))
    return r_repost_count


def get_yt_video_id(value):
    """
    Example URL's that can be parsed:
    - http://youtu.be/SA2iWivDJiE
    - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    - http://www.youtube.com/movie?v=_oPAwA_Udwc&feature=feedu
    - http://www.youtube.com/attribution_link?a=AbE6fYtNaa4&u=%2Fwatch%3Fv%3DNbyHNASFi6U%26feature%3Dshare
    - http://www.youtube.com/embed/SA2iWivDJiE
    - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    """
    query = urlparse(value)
    pattern = re.compile('[^\w-].*$')
    if query.hostname == 'youtu.be':
        return pattern.sub('',query.path[1:])
    if query.hostname in yt_hostnames:
        if query.path == '/watch' or query.path == '/movie':
            p = parse_qs(query.query)
            return pattern.sub('',p['v'][0])
        if query.path == '/attribution_link':
            p = parse_qs(query.query)
            p = urlparse(p['u'][0])
            p = parse_qs(p.query)
            return pattern.sub('',p['v'][0])
        if query.path[:7] == '/embed/':
            return pattern.sub('',query.path.split('/')[2])
        if query.path[:3] == '/v/':
            return pattern.sub('',query.path.split('/')[2])
    raise ValueError('No video ID could be extracted from URL %s' % value)


def get_yt_service():
    return build(yt_api_service_name, yt_api_version,
                 developerKey=yt_developer_key)

def r_refresh_login():
    global r_access_information
    global r
    global r_last_refresh
    if (time.time() - r_last_refresh) > r_refresh_login_interval:   
        r_access_information =  r.refresh_access_information(r_refresh_token)
        r_last_refresh = time.time()


def r_login():
    global r_access_information
    global r
    r = praw.Reddit(r_praw)
    r.set_oauth_app_info(client_id=r_client_id, client_secret=r_client_secret,
                         redirect_uri=r_redirect_uri)
    r_refresh_login()



def connect_database():
    global c
    global conn
    conn = sqlite3.connect(sql_db)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS processed (submissionId TEXT NOT NULL);')
    conn.commit()


def r_get_subreddit():
    return r.get_subreddit(r_subredit)
    

def r_get_submissions():
    bot_sleep()
    return subreddit.get_new(limit=bot_subsLimit)


def get_yt_video_entry(my_yt_video_id):
    return yt_service.videos().list(id=my_yt_video_id, 
                                    part='snippet,statistics').execute()


def get_yt_upload_date(my_yt_video_entry):
    try:
        yt_upload_date = my_yt_video_entry["items"][0]["snippet"]["publishedAt"]
    except:
        yt_upload_date = "err"
    return yt_upload_date


def get_yt_view_count(my_yt_video_entry):
    try:
        yt_view_count = my_yt_video_entry["items"][0]["statistics"]["viewCount"]
    except:
        yt_view_count = "err"
    return yt_view_count


def get_yt_comment_count(my_yt_video_entry):
    try:
        yt_comment_count = my_yt_video_entry["items"][0]["statistics"]["commentCount"]
    except:
        yt_comment_count = 0
    return yt_comment_count


def get_yt_dislike_count(my_yt_video_entry):
    try:
        yt_dislike_count = my_yt_video_entry["items"][0]["statistics"]["dislikeCount"]
    except:
        yt_dislike_count = 0
    return yt_dislike_count


def get_yt_favorite_count(my_yt_video_entry):
    try:
        yt_favorite_count = my_yt_video_entry["items"][0]["statistics"]["favoriteCount"]
    except:
        yt_favorite_count = 0
    return yt_favorite_count


def get_yt_like_count(my_yt_video_entry):
    try:
        yt_like_count = my_yt_video_entry["items"][0]["statistics"]["likeCount"]
    except:
        yt_like_count = 0
    return yt_like_count


def get_yt_channel_text(my_yt_video_entry):
    yt_channel_title = my_yt_video_entry["items"][0]["snippet"]["channelTitle"]
    yt_channel_title = yt_channel_title.replace('\\' ,'\\\\')
    yt_channel_title = yt_channel_title.replace('[','\[')
    yt_channel_title = yt_channel_title.replace(']','\]')
    yt_channel_title = yt_channel_title.replace('(','\(')
    yt_channel_title = yt_channel_title.replace(')','\)')
    yt_channel_title = yt_channel_title.replace('|',unichr(9474))
    yt_channel_id = my_yt_video_entry["items"][0]["snippet"]["channelId"]
    yt_channel_text = "[%s](http://www.youtube.com/channel/%s)" % (
                       yt_channel_title, yt_channel_id)
    return yt_channel_text


def get_yt_title(my_yt_video_entry):
    yt_title = my_yt_video_entry["items"][0]["snippet"]["title"]
    yt_title = yt_title.replace('\\' ,'\\\\')
    yt_title = yt_title.replace('[','\[')
    yt_title = yt_title.replace(']','\]')
    yt_title = yt_title.replace('(','\(')
    yt_title = yt_title.replace(')','\)')
    yt_title = yt_title.replace('|',unichr(9474))
    return yt_title


def get_comment_text(my_yt_video_id, my_yt_video_entry, my_r_submission, my_r_subredit):
    r_repost_count = get_repost_count(my_yt_video_id, my_r_subredit)
    yt_upload_date = get_yt_upload_date(my_yt_video_entry)
    yt_view_count = get_yt_view_count(my_yt_video_entry)
    yt_comment_count = get_yt_comment_count(my_yt_video_entry)
    yt_dislike_count = get_yt_dislike_count(my_yt_video_entry)
    yt_favorite_count = get_yt_favorite_count(my_yt_video_entry)
    yt_like_count = get_yt_like_count(my_yt_video_entry)
    yt_channel_text = get_yt_channel_text(my_yt_video_entry)
    yt_title = get_yt_title(my_yt_video_entry)
    r_comment_text = "Information about this YouTube video as seen on %s:\n\n" %  time.strftime("%c %Z")
    r_comment_text += "Item | Value\n"
    r_comment_text += "---|---\n"
    r_comment_text += "Channel | %s\n" % yt_channel_text
    r_comment_text += "Title | [%s](%s)\n" % (yt_title, my_r_submission.url)
    r_comment_text += "View Count | %s\n" % yt_view_count
    r_comment_text += "Upload Date | %s\n" % yt_upload_date
    r_comment_text += "Repost Count | [%s]" % r_repost_count
    r_comment_text += "(http://www.reddit.com/r/{0}/search?q=url%3A%22{1}%22&restrict_sr=on)\n".format(
                       my_r_subredit, my_yt_video_id)
    r_comment_text += "Favorite Count | %s\n" % yt_favorite_count
    r_comment_text += "Like Count | %s\n" % yt_like_count
    r_comment_text += "Dislike Count | %s\n" % yt_dislike_count
    r_comment_text += "\n"
    r_comment_text += bot_info_text
    return r_comment_text


def r_mod_comment(my_r_submission, my_r_comment_text):
    modcomment = my_r_submission.add_comment(my_r_comment_text)
    modcomment.distinguish(as_made_by='mod')

