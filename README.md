# Secure Remote Command Execution System

## Overview
This project implements a secure client-server system in Python that allows authenticated users to execute commands remotely over an encrypted connection using SSL/TLS.

## Features
- Secure communication using SSL/TLS
- User authentication (username and password)
- Protection against multiple failed login attempts
- Role-based command execution
- Logging of user activity and commands
- Multi-client support using threading
- JSON-based communication

## Project Structure
secure_remote_command/
|
|-- client.py
|-- server.py
|-- auth.py
|-- command_handler.py
|-- logger.py
|-- certs/
|   |-- server.crt
|   |-- server.key
|-- logs/
|-- .gitignore
|-- README.md

## Setup Instructions

1. Clone Repository
git clone https://github.com/tanvimag/secure_remote_command_execution.git
cd secure_remote_command_execution

2. Create Virtual Environment (optional)
python3 -m venv venv

Activate:
source venv/bin/activate

3. Install Dependencies
pip install -r requirements.txt

4. Generate SSL Certificates
openssl req -new -x509 -days 365 -nodes -out certs/server.crt -keyout certs/server.key

## Execution Steps

1. Start Server

```bash
python3 server.py
```

2. Run Client (in another terminal)

```bash
python3 client.py
```

3. Authentication
Enter username and password when prompted

4. Execute Commands
Example:
```bash
ls
whoami
exit
```

5. Performance Analysis
```bash
python3 performance_test.py
```

## Security Features
- Encrypted communication using SSL/TLS
- Secure transmission of credentials
- Login attempt tracking and blocking
- Role-based access control

## Logging
All activities are stored in logs/ directory

## Important Notes
- Do NOT upload server.key to GitHub
- Use .gitignore to exclude:
  venv/
  __pycache__/
  *.key

## Future Improvements
- GUI interface
- Database authentication
- File transfer support

