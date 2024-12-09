import requests
from rest_framework.exceptions import ValidationError
from django.conf import settings

OBSTRACT_SERVICE_API = settings.OBSTRACT_SERVICE_API


def get_obstracts_job(feed_id, job_id):
    response = requests.get(
        OBSTRACT_SERVICE_API + f"/feeds/{feed_id}/jobs/{job_id}/",
    )
    response.raise_for_status()
    return response.json()


def create_obstracts_feed(
    profile_id,
    url,
    include_remote_blogs,
    pretty_url,
    description,
    title,
):
    data = {
        "profile_id": str(profile_id),
        "url": url,
        "include_remote_blogs": include_remote_blogs,
        "pretty_url": pretty_url,
        "description": description,
        "title": title,
    }
    response = requests.post(
        OBSTRACT_SERVICE_API + "/feeds/",
        json=data,
    )
    if (response.status_code == 400):
        raise ValidationError(response.json())
    response.raise_for_status()
    return response.json()


def create_obstracts_skeleton_feed(
    url,
    pretty_url,
    description,
    title,
):
    data = {
        "url": url,
        "pretty_url": pretty_url,
        "description": description,
        "title": title,
    }
    response = requests.post(
        OBSTRACT_SERVICE_API + "/feeds/skeleton/",
        json=data,
    )
    if (response.status_code == 400):
        raise ValidationError(response.json())
    response.raise_for_status()
    return response.json()


def delete_obstracts_feed(feed_id):
    return requests.delete(f"{OBSTRACT_SERVICE_API}/feeds/{feed_id}/")


def get_obstracts_feed(feed_id):
    url = f"{OBSTRACT_SERVICE_API}/feeds/{feed_id}/"
    print(url)
    return requests.get(url).json()


def init_reload_feed(profile_id, feed_id):
    data = {
        "profile_id": str(profile_id),
        "include_remote_blogs": False,
    }
    response = requests.patch(
        OBSTRACT_SERVICE_API + f"/feeds/{feed_id}/fetch/",
        json=data,
    )
    response.raise_for_status()
    return response.json()


def get_post_for_report_object(object):
    external_references = object['external_references']
    obstracts_feed = next(filter(lambda external_reference: external_reference['source_name'] == 'obstracts_feed_id', external_references), None)
    txt2stix_report = next(filter(lambda external_reference: external_reference['source_name'] == 'txt2stix_report_id', external_references), None)
    if not obstracts_feed or not txt2stix_report:
        return {}
    feed_id = obstracts_feed['external_id']
    post_id = txt2stix_report['external_id']
    response = requests.get(
        OBSTRACT_SERVICE_API + f"/feeds/{feed_id}/posts/{post_id}/",
    )
    response.raise_for_status()
    post = response.json()
    post['feed_id'] = feed_id
    return post, feed_id


def get_posts_by_extractions(object_id, page):
    response = requests.get(
        OBSTRACT_SERVICE_API + f"/object/{object_id}/reports/",
        params={"page": page}
    )
    response.raise_for_status()
    report_objects = response.json()["reports"]
    posts = []
    feed_id_dict = {}
    for report_object in report_objects:
        post, feed_id = get_post_for_report_object(report_object)
        post_id = post.get('id')
        feed_id_dict[feed_id] = True
        posts.append(post)
    return posts, feed_id_dict.keys(), response.json()


def get_latest_posts(feed_ids, sort, title, page):
    if feed_ids == []:
        return {
            "page_size": 10,
            "page_number": 1,
            "page_results_count": 0,
            "total_results_count": 0,
            "posts": [],
        }
    
    response = requests.get(
        OBSTRACT_SERVICE_API + f"/posts/",
        params={
            "feed_id": feed_ids,
            "page": page,
            "page_size": 10,
            "title": title,
            "sort": sort,
        }
    )
    response.raise_for_status()
    response_data = response.json()
    return response_data
