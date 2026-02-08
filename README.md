# 🌤️ WeatherBot

A versatile Telegram bot that delivers weather updates right to your chat. Get daily automated forecasts at your preferred time or request weather updates anytime you want!

## ✨ Features

- **Daily Weather Notifications**: Set a custom time to receive weather updates automatically every day
- **On-Demand Weather**: Get current weather conditions anytime with a simple command
- **Location Flexibility**: Use your Telegram geolocation or set a specific city
- **Simple Commands**: Easy-to-use interface with intuitive commands

## 🚀 Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and get started |
| `/help` | Display the list of available commands |
| `/weather` | Get current weather conditions |
| `/settime HH:MM` | Set your daily notification time (24-hour format) |
| `/setcity` | Change your default city for weather updates |
| `/mylocation` | Use your Telegram geolocation for weather data |

## 📋 Prerequisites

To run this bot locally, you'll need:

- Python 3.7+
- A Telegram Bot Token from [@BotFather](https://t.me/botfather)
- OpenWeatherMap API key (or your preferred weather service)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/dapolet/WeatherBot.git
   cd WeatherBot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   WEATHER_API_KEY=your_weather_api_key_here
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

## 🎯 Usage

1. Search for your bot on Telegram
2. Start a chat and send `/start`
3. Set your location using either:
   - `/mylocation` (send your geolocation)
   - `/setcity` (enter your city name)
4. Set your preferred notification time with `/settime HH:MM`
5. Enjoy daily weather updates!

## 🔧 Configuration

The bot uses environment variables for configuration. Make sure to set:

- `TELEGRAM_BOT_TOKEN`: Obtained from [@BotFather](https://t.me/botfather)
- `WEATHER_API_KEY`: From [OpenWeatherMap](https://openweathermap.org/api) or similar service

## 📁 Project Structure

```
WeatherBot/
├── bot.py              # Main bot logic
├── requirements.txt    # Python dependencies
├── .env.example       # Example environment variables
├── README.md          # This file
└── data/              # User data storage (if applicable)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👤 Author

**dapolet**
- GitHub: [@dapolet](https://github.com/dapolet)

## 🙏 Acknowledgments

- Telegram for their excellent Bot API
- OpenWeatherMap for weather data (or your chosen weather service)
- All contributors and users of WeatherBot

## ⚠️ Disclaimer

This bot is for personal/educational use. Weather data accuracy depends on the weather service provider used.

---

⭐ Star this repo if you find it useful!
