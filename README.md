# MGSymposiumBot

MGSymposiumBot is an asynchronous Telegram bot built using Python and the aiogram library. The bot is designed to manage symposium data and includes full CRUD (Create, Read, Update, Delete) functionality for interacting with a PostgreSQL database using SQLAlchemy in asynchronous mode. Additionally, Docker is used for deployment and orchestration.

### 🚀 Features

	•	Asynchronous operations for smooth performance.
	•	CRUD functionality for managing symposium-related data.
	•	PostgreSQL database integration using SQLAlchemy and asyncpg.
	•	Docker support for easy setup and deployment.

### 📦 Installation

#### 1. Clone the repository:
To get started with this project, follow the steps below:

```
git clone https://github.com/yourusername/MGSymposiumBot.git
cd MGSymposiumBot
```

#### 2. Install dependencies using Poetry:
You need to install [poetry](https://python-poetry.org/docs/#installation) to use this project
```
make install
```

#### 3. Activate the virtual environment:

```
make shell
```

#### 4. Create the .env file:
In the root of your project directory, create a `.env` file with the following content:
```
BOT_TOKEN=<your-telegram-bot-token>
OWNER_ID=<your-telegram-user-id>
MGSU_DEFAULT_LOGO=<your-default-url-logo-token>
DATABASE_URL=postgresql+asyncpg://MGSU:<your-db-password>@postgres:5432/symposium
```

Replace `<your-telegram-bot-token>`, `<your-telegram-user-id>`, `<your-default-url-logo-token>`, and `<your-db-password>` with your actual credentials.


### 🛠️ Run project

To run the project use the following command:

```
make start
```



### 🧑‍💻 Usage

Once the bot is running, it will automatically respond to user input based on the implemented business logic. Ensure your PostgreSQL database is set up correctly and connected via the .env configuration.

### ⚙️ Technology Stack

	•	Python 3.9
	•	Aiogram 3.13.0 - A fully asynchronous Telegram Bot API framework.
	•	SQLAlchemy (with asyncio) - ORM for database management.
	•	PostgreSQL - Database used to store symposium data.
	•	Asyncpg - PostgreSQL driver for asynchronous interaction.
	•	Alembic - For handling database migrations.
	•	Docker - For containerization and orchestration.