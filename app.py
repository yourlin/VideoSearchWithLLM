import json
from urllib.parse import urlparse
import streamlit as st
import requests
from config import *

import boto3
from botocore.exceptions import ClientError

# Generate a presigned URL for the S3 object
s3_client = boto3.client('s3',
                         aws_access_key_id=AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


def create_presigned_url_from_s3_uri(s3_uri, expiration=3600):
    """
    Generate a presigned URL for an S3 object using its S3 URI

    :param s3_uri: string, S3 URI in the format s3://bucket-name/object-key
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """
    # Parse the S3 URI
    parsed_uri = urlparse(s3_uri)
    if parsed_uri.scheme != 's3':
        raise ValueError("Invalid S3 URI scheme. Expected 's3://'")

    bucket_name = parsed_uri.netloc
    object_key = parsed_uri.path.lstrip('/')

    try:
        presign_url = s3_client.generate_presigned_url('get_object',
                                                       Params={'Bucket': bucket_name,
                                                               'Key': object_key},
                                                       ExpiresIn=expiration)
        # The response contains the presigned URL
        return presign_url
    except ClientError as e:
        print(f"Error: {e}")
        return None


def timestamp_to_seconds(timestamp):
    """
    将时间戳格式 'HH:MM:SS' 转换为秒数

    :param timestamp: 字符串格式的时间戳，例如 '00:13:57'
    :return: 对应的秒数
    """
    # 分割时间戳
    hours, minutes, seconds = map(int, timestamp.split(':'))

    # 计算总秒数
    total_seconds = hours * 3600 + minutes * 60 + seconds

    return total_seconds


# 显示视频函数
def display_video(s3_uri, checklist_url, subtitles=None, description=None, timestamp=None, item_id=None):
    try:
        # 使用 st.video 显示视频
        col1, col2 = st.columns([2,1])
        with col2:
            with st.expander("查看相关的问卷"):
                st.markdown("### Show Time")
                questionnaire = get_s3_object(checklist_url)
                display_questionnaire(questionnaire, item_id)
        with col1:
            # 如果有标题
            if subtitles:
                st.markdown(f"### {subtitles}")


            presign_url = create_presigned_url_from_s3_uri(
                s3_uri)
            st.video(presign_url,
                     format="video/mp4",
                     start_time=timestamp_to_seconds(timestamp)
                     )

            # 显示描述
            if description:
                # st.markdown("### Description:")
                st.caption(description)



        st.write("---")

    except ClientError as e:
        st.error(f"Error accessing S3: {str(e)}")
    except Exception as e:
        st.error(f"Error displaying video: {str(e)}")


def get_s3_object(s3_uri):
    # Parse the S3 URI
    parsed_uri = urlparse(s3_uri)

    if parsed_uri.scheme != 's3':
        raise ValueError("Invalid S3 URI scheme. Expected 's3://'")

    bucket_name = parsed_uri.netloc
    object_key = parsed_uri.path.lstrip('/')
    try:
        # 获取对象
        s3_res = s3_client.get_object(Bucket=bucket_name, Key=object_key)

        # 读取对象内容
        content = s3_res['Body'].read().decode('utf-8')

        # 解析 JSON 内容
        json_data = json.loads(content)

        index = json_data['data']['outputs']['text'].find('[')
        res = json_data['data']['outputs']['text'][index:]
        return json.loads(res)
    except Exception as e:
        print(f"发生错误: {str(e)}")


def display_questionnaire(questions, item_id=0):
    if 'score' not in st.session_state:
        st.session_state.score = 0

    # 初始化答题状态
    if 'answered' not in st.session_state:
        st.session_state.answered = [False] * len(questions)

    # 遍历每个问题
    for i, question in enumerate(questions):
        st.markdown(f"##### Question {i + 1}: {question['question']}")

        # 为每个选项创建一个 checkbox
        for option in question['options']:
            key = f"q{i}_o{option['index']}_{item_id}"
            checked = st.checkbox(
                option['content'],
                key=key,
                disabled=st.session_state.answered[i]
            )

            # 如果选中了一个选项
            if checked and not st.session_state.answered[i]:
                st.session_state.answered[i] = True

                # 检查答案是否正确
                if option['index'] == question['answer']:
                    st.success("Correct!")
                    st.session_state.score += 1
                else:
                    st.error(f"Wrong. The correct answer is: {question['options'][question['answer']]['content']}")

                # 更新选项状态
                for other_option in question['options']:
                    other_key = f"q{i}_o{other_option['index']}"
                    if other_key != key:
                        st.session_state['other_key'] = False

                # st.experimental_rerun()

        st.write("---")

    # 显示总分
    total_questions = len(questions)
    answered_questions = sum(st.session_state.answered)
    if answered_questions == total_questions:
        st.success(f"Quiz completed! Your score: {st.session_state.score}/{total_questions}")
    else:
        st.info(f"Questions answered: {answered_questions}/{total_questions}")
        st.info(f"Current score: {st.session_state.score}/{total_questions}")


# 设置页面配置
st.set_page_config(
    page_title="视频智能检索",
    page_icon=":robot:",
    layout="wide"
)

col_logo, col_title = st.columns([1, 7])
with col_logo:
    sidebar_logo = "images/logo.png"
    st.image(sidebar_logo, width=80)

with col_title:
    st.title("企业知识检索")

# 初始化会话状态
if 'generated' not in st.session_state:
    st.session_state['generated'] = []
if 'past' not in st.session_state:
    st.session_state['past'] = []

# 创建标签页
# tab1, tab2 = st.tabs(["视频智能检索", "智能考卷"])

# 在第一个标签页中添加内容
# with tab1:
# 输入问题
user_input = st.text_input("您的问题:", key="input")


# Dify API 调用函数
def dify_api_call(input, key=None):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": input,
        "response_mode": "blocking",
        "user": "python"
    }

    response = requests.post(f'{DIFY_API_URL}/workflows/run', headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        if data['data']["status"] == 'succeeded':
            return data['data']['outputs']

        return []
    else:
        st.error(f"调用 Dify API 时出错: {response.status_code}")
        return None


# 处理用户输入
if user_input:
    response = dify_api_call({"input": user_input}, DIFY_API_KEY)
    if response:
        st.session_state.past.append(user_input)
        st.session_state.generated.append(response)

        for i, item in enumerate(response['res']):
            display_video(item['s3_url'],
                          item['checklist_url'],
                          subtitles=item['title'],
                          description=item['description'],
                          timestamp=item['start_time'],
                          item_id=i)
