import logging
logging.basicConfig(level=logging.INFO)
import speechmatics
import asyncio
import argparse
import sys
import sounddevice as sd
import aioconsole
import os

from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

from elevenlabs import generate, play, set_api_key, clone

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SPEECHMATICS_API_KEY = os.getenv("SPEECHMATICS_API_KEY", "")
assert ELEVEN_API_KEY, f"Please set {ELEVEN_API_KEY}"
assert OPENAI_API_KEY, f"Please set {OPENAI_API_KEY}"
assert SPEECHMATICS_API_KEY, f"Please set {SPEECHMATICS_API_KEY}"

set_api_key(ELEVEN_API_KEY)


def create_speechmatics_client(speechmatics_url: str):
    conn = speechmatics.models.ConnectionSettings(
        url=speechmatics_url,
        auth_token=SPEECHMATICS_API_KEY,
    )
    return speechmatics.client.WebsocketClient(conn)


def format_text(current_transcript: list):
        sorted_values = list(map(lambda x: x[1], sorted(current_transcript.items())))
        try:
            first_non_eos = next(i for i, token in enumerate(sorted_values) if 'is_eos' not in token)
            sorted_values = sorted_values[first_non_eos:]
        except StopIteration:
            pass
        def get_text_token(token):
            content = token['alternatives'][0]['content']
            if 'is_eos' not in token:
                return ' ' + content 
            return content

        return ''.join([get_text_token(x) for x in sorted_values])

def override_transcript(keyed_transcript, current_transcript, is_final):
    for start_time, token in keyed_transcript.items():
        if start_time not in current_transcript or is_final or token['alternatives'][0]['confidence'] >= current_transcript[start_time]['alternatives'][0]['confidence']:
            current_transcript[start_time] = token


def discard_partials(current_transcript):
    return {k: v for k, v in current_transcript.items() if v['final']}

def discard_old_transcript(current_transcript, current_duration, seconds_to_keep = 8):
    return {k: v for k, v in current_transcript.items() if k > (current_duration - seconds_to_keep)}

current_transcript = dict()
text = None
prev_text = None
TERMINATE_WORD = "abracadabra"

async def check_for_done():
    global text
    global prev_text
    counter = 0
    while True:
        if text is not None and prev_text is None:
            print("Listening...")
        if text is not None and TERMINATE_WORD in text.lower():
            text = text.replace(TERMINATE_WORD, "").replace(TERMINATE_WORD.capitalise(), "").strip()
            raise TimeoutError
        # increment counter if text hasn't changed
        if prev_text is not None and text.replace(".","").lower() == prev_text.replace(".","").lower():
            counter += 0.5
            print(counter)
        else:
            counter = 0
            prev_text = text
        if counter > 2:
            raise TimeoutError
        await asyncio.sleep(0.5)

async def check_key_press():
    while True:
        if await aioconsole.ainput() is not None:
            raise TimeoutError


def init(sm_client):
    def update_rolling_transcript(msg):
        global current_transcript
        global text
        global prev_text
        is_final =  msg['message'] == 'AddTranscript'
        # current_time = time.time()
        # duration = current_time - TRANSCRIPTION_START_TIME
        keyed_transcript = dict(map(lambda x: (round(x['start_time'], 3),{ **x, 'final': is_final}), msg['results']))

        if is_final and len(keyed_transcript) > 0:
            current_transcript = discard_partials(current_transcript)

        override_transcript(keyed_transcript, current_transcript, is_final)
        # current_transcript = discard_old_transcript(current_transcript, duration)

        if len(current_transcript) > 0:
            prev_text = text
            text = format_text(current_transcript).strip()
            # os.system('clear')
            print(text)
            # sys.stdout.write("\033[F") # Cursor up one line

    sm_client.add_event_handler(speechmatics.models.ServerMessageType.AddPartialTranscript, event_handler=update_rolling_transcript)
    sm_client.add_event_handler(speechmatics.models.ServerMessageType.AddTranscript, event_handler=update_rolling_transcript)

    logging.info('Connecting...')
    return True

class RawInputStreamWrapper:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def read(self, frames):
        return bytes(self.wrapped.read(frames)[0])


async def transcribe_from_device(device, speechmatics_client):
    frame_rate=44_100
    with sd.RawInputStream(device=device, channels=1, samplerate=frame_rate, dtype='float32') as stream:
        settings = speechmatics.models.AudioSettings(
            sample_rate=frame_rate,
            chunk_size=1024*4,
            encoding="pcm_f32" + ("le" if sys.byteorder == "little" else "be"),
        )
        # Define transcription parameters
        conf = speechmatics.models.TranscriptionConfig(language='en',operating_point="enhanced", max_delay=2, enable_partials=True, enable_entities=True)
        await speechmatics_client.run(RawInputStreamWrapper(stream), conf, settings)


async def main(args):
    global text
    global prev_text
    global current_transcript
    speechmatics_client = create_speechmatics_client(args.speechmatics_url)
    init(speechmatics_client)

    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
    memory = ConversationBufferMemory()
    if args.llm_system_prompt:
        memory.chat_memory.add_ai_message(args.llm_system_prompt)
    conversation = ConversationChain(
        llm=llm, 
        verbose=True, 
        memory=memory
    )
    
    if args.voice_file:
        print("Cloning voice")
        voice = clone(
            name=args.voice_name,
            description=args.voice_description,
            files=[args.voice_file],
        )
        print("Finished cloning")
    else:
        voice = args.voice_name


    while True:
        tasks = [transcribe_from_device(args.device, speechmatics_client), check_for_done(), check_key_press()]
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            # Handle the exception when one of the tasks fails
            print(f"An error occurred: {e}")
        
        if text:
            response = conversation.predict(input=text)
            print(f"User: {text}")
            print(f"AI: {response}")
            audio = generate(text=response, voice=voice)
            play(audio)
        else:
            print("Nothing was said!")
        
        text = None
        prev_text = None
        current_transcript = dict()

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Speechmatics realtime chat')
    parser.add_argument('--speechmatics_url', type=str, default="wss://eu.rt.speechmatics.com/v2/en", help='Speechmatics websocket url')
    parser.add_argument('--llm_system_prompt', type=str, default=None, help='LLM system prompt')
    parser.add_argument('--voice_name', type=str, default="Adam", help='voice name')
    parser.add_argument('--voice_description', type=str, default="", help='voice description')
    parser.add_argument('--voice_file', type=str, default=None, help='voice file for cloning')

    parser.add_argument('-d', '--device', type=int_or_str, help='input device (numeric ID or substring)')

    asyncio.run(main(parser.parse_args()))