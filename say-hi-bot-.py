import irc.bot
import irc.strings
import logging
import time

# Configuration
server_address = 'irc.wetfish.net'  # Server address
port = 6697  # SSL port
channel = '#wetfish'  # Channel to join
nickname = 'sayhi'  # Bot's nickname

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("moodawarebot.log"),  # Log to a file
        logging.StreamHandler()  # Log to console
    ]
)

class MoodAwareBot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        # Setup bot with server, port, and nickname
        server = [(server_address, port)]  # Use renamed variable here
        irc.bot.SingleServerIRCBot.__init__(self, server, nickname, nickname)

        logging.info(f"Bot {nickname} initialized.")

    def on_welcome(self, connection, event):
        # Called when the bot successfully connects to the IRC server
        logging.info(f"Successfully connected to {server_address} as {nickname}.")
        self.connection.join(channel)
        logging.info(f"Joined channel {channel}.")

        # Send a "Hi" message to the channel
        self.connection.privmsg(channel, "Hi")
        logging.info(f"Sent message: 'Hi' to {channel}.")

    def on_pubmsg(self, connection, event):
        # Log any messages from users in the channel
        logging.info(f"Message from {event.source.nick}: {event.arguments[0]}")

    def on_ping(self, connection, event):
        # Respond to PING messages to keep the connection alive
        logging.debug(f"Received PING: {event.arguments[0]}")
        connection.pong(event.arguments[0])
        logging.debug("Sent PONG response.")

    def on_disconnect(self, connection, event):
        # Called when the bot gets disconnected from the IRC server
        logging.error(f"Disconnected from {server_address}. Reconnecting in 10 seconds...")
        time.sleep(10)  # Optional: wait before trying to reconnect
        self.start()  # Reconnect the bot

    def on_error(self, connection, event):
        # This logs unexpected errors that may occur during the connection
        logging.error(f"Error occurred: {event}")

# Create and start the bot
bot = MoodAwareBot()
bot.start()
