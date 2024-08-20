import streamlit as st
from streamlit_chat import message
import requests
import json

# Dify API 配置
DIFY_API_KEY = "your_dify_api_key"
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"

# 设置页面标题
st.set_page_config(page_title="视频智能检索")

# 初始化会话状态
if 'generated' not in st.session_state:
    st.session_state['generated'] = []
if 'past' not in st.session_state:
    st.session_state['past'] = []

# 创建 Q&A 界面
st.title("视频智能检")

# 输入问题
user_input = st.text_input("您的问题:", key="input")


# Dify API 调用函数
def dify_api_call(question):
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": {},
        "query": question,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "user"
    }

    response = requests.post(DIFY_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        return {
            'answer': data['answer'],
            'video_uri': data.get('video_uri'),
            'timestamp': data.get('timestamp')
        }
    else:
        st.error(f"调用 Dify API 时出错: {response.status_code}")
        return None


# 显示视频函数
def display_video(video_uri, timestamp):
    try:
        # 直接使用返回的预签名 URL
        st.video(video_uri, start_time=int(timestamp))
    except Exception as e:
        st.error(f"显示视频时出错: {str(e)}")


# 处理用户输入
if user_input:
    response = dify_api_call(user_input)

    if response:
        st.session_state.past.append(user_input)
        st.session_state.generated.append(response['answer'])

        # 检查是否有视频文件和时间戳
        if 'video_uri' in response and 'timestamp' in response:
            display_video(response['video_uri'], response['timestamp'])

# 显示对话历史
if st.session_state['generated']:
    for i in range(len(st.session_state['generated']) - 1, -1, -1):
        message(st.session_state["generated"][i], key=str(i))
        message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')
