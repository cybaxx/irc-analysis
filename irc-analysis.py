import irc.bot
import threading
import sqlite3
from textblob import TextBlob
from configobj import ConfigObj
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mood_aware_bot.log"),
        logging.StreamHandler()
    ]
)

class DatabaseManager:
    """Handles database operations related to user preferences and sentiment history."""

    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        """Establish a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)

    def setup_db(self):
        """Setup SQLite database and create necessary tables."""
        conn = self._connect()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS preferences (
                        user_id INTEGER PRIMARY KEY,
                        enable_mood_checks BOOLEAN,
                        check_interval INTEGER,
                        mood_threshold REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sentiment_history (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        message TEXT,
                        sentiment TEXT,
                        polarity REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES preferences(user_id))''')
        conn.commit()
        conn.close()
        logging.debug("Database setup complete.")

    def get_user_preferences(self, user_id):
        """Fetch user preferences."""
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result

    def set_user_preferences(self, user_id, enable_mood_checks, check_interval, mood_threshold):
        """Store user preferences."""
        conn = self._connect()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO preferences (user_id, enable_mood_checks, check_interval, mood_threshold)
                     VALUES (?, ?, ?, ?)''',
                  (user_id, enable_mood_checks, check_interval, mood_threshold))
        conn.commit()
        conn.close()

    def log_sentiment(self, user_id, message, sentiment, polarity):
        """Log a user's sentiment history."""
        conn = self._connect()
        c = conn.cursor()
        c.execute('''INSERT INTO sentiment_history (user_id, message, sentiment, polarity)
                     VALUES (?, ?, ?, ?)''',
                  (user_id, message, sentiment, polarity))
        conn.commit()
        conn.close()

class SentimentAnalyzer:
    """Class to handle sentiment analysis using TextBlob."""

    @staticmethod
    def analyze_sentiment(text):
        """Analyze sentiment using TextBlob."""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        logging.debug(f"Analyzing sentiment for message: {text}")
        if polarity > 0.1:
            return 'Positive', polarity
        elif polarity < -0.1:
            return 'Negative', polarity
        else:
            return 'Neutral', polarity

class MoodAwareAI:
    """AI class to manage user preferences, sentiment analysis, and periodic checks."""

    def __init__(self, config_file='config.ini', db_path='user_preferences.db'):
        self.config = ConfigObj(config_file)
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.setup_db()
        self.latest_message = None

    def analyze_message(self, message, user_id):
        """Analyze sentiment from a message and store user sentiment history."""
        sentiment, polarity = SentimentAnalyzer.analyze_sentiment(message)
        self.db_manager.log_sentiment(user_id, message, sentiment, polarity)
        self.latest_message = (message, sentiment, polarity)
        return sentiment, polarity

    def get_latest_message(self):
        """Retrieve the latest message and its sentiment."""
        return self.latest_message

    def get_user_preferences(self, user_id):
        """Retrieve user preferences."""
        return self.db_manager.get_user_preferences(user_id)

    def update_user_preferences(self, user_id, enable_mood_checks, check_interval, mood_threshold):
        """Update user preferences in the database."""
        self.db_manager.set_user_preferences(user_id, enable_mood_checks, check_interval, mood_threshold)

class MoodCheckBot(irc.bot.SingleServerIRCBot):
    """IRC bot that checks the mood of messages in the channel and responds accordingly."""

    def __init__(self, server, port, channel, nickname, mood_ai):
        self.server = server
        self.port = port
        self.channel = channel
        self.nickname = nickname
        self.mood_ai = mood_ai

        # Initialize IRC bot
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)

        # Start periodic mood checks
        self.schedule_periodic_mood_check()

    def on_welcome(self, c, e):
        """Called when the bot successfully joins the channel."""
        logging.info(f"Connected to {self.server}:{self.port}, joining channel: {self.channel}")
        c.join(self.channel)
        self.display_banner(c)

    def on_pubmsg(self, c, e):
        """Called when a public message is received in the channel."""
        message = e.arguments[0]
        user = e.source.split('!')[0]
        sentiment, score = self.mood_ai.analyze_message(message, user)
        logging.debug(f"Processed message: '{message}' | Sentiment: {sentiment} | Score: {score}")

        # Respond based on sentiment
        if sentiment == 'Positive':
            c.privmsg(self.channel, f"{user}, that's awesome! Keep it up!")
        elif sentiment == 'Negative':
            c.privmsg(self.channel, f"{user}, I'm here for you if you need anything.")
        else:
            c.privmsg(self.channel, f"{user}, how can I help today?")

    def schedule_periodic_mood_check(self):
        """Schedule periodic mood checks."""
        threading.Timer(300, self.check_and_respond_periodically).start()  # 5-minute interval

    def check_and_respond_periodically(self):
        """Check and respond periodically based on the latest sentiment."""
        latest_message = self.mood_ai.get_latest_message()
        if latest_message:
            message, sentiment, score = latest_message
            logging.debug(f"Periodic sentiment check: {sentiment} for message: {message} (Score: {score})")

            if sentiment == 'Positive':
                response = f"Great mood! Keep it up! ({message})"
            elif sentiment == 'Negative':
                response = f"Hang in there! We're here for you. ({message})"
            else:
                response = f"Neutral mood, feel free to talk to me! ({message})"

            self.connection.privmsg(self.channel, response)

        self.schedule_periodic_mood_check()

    def start_bot(self):
        """Run the IRC bot in a separate thread."""
        bot_thread = threading.Thread(target=self.start)
        bot_thread.start()

def main():
    server = 'irc.wetfish.net'
    port = 6697
    channel = '#wetfish'
    nickname = 'MoodAwareBot'

    # Initialize AI and IRC bot
    ai = MoodAwareAI()
    bot = MoodCheckBot(server, port, channel, nickname, ai)
    bot.start_bot()

if __name__ == '__main__':
    main()
