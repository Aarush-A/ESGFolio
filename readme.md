# ESGFolio

## Overview

In today’s investment landscape, the consideration of Environmental, Social, and Governance (ESG) factors is increasingly crucial in portfolio management. This application is designed to evaluate and rate portfolio ESG scores based on weighted factor fields using multi-criteria decision-making. The app assesses companies across various sectors using specific ESG criteria such as fossil fuel involvement, deforestation practices, gender equality metrics, firearms and prison industry engagements, and tobacco affiliations. Each criterion is assigned a weighted score reflecting its impact on ESG performance.

## Features

- **User Authentication**: Secure registration and login functionality.
- **Portfolio Management**: Users can add, view, and delete companies from their portfolios.
- **ESG Scoring**: Comprehensive ESG scores based on multiple criteria for each company in the user's portfolio.
- **Visualizations**: Graphical representations including bar and radar charts to compare personal ESG scores against average scores of all users.
- **Search Functionality**: Search for companies to view their ESG scores and add them to the portfolio.
- **Session Management**: User sessions are managed securely to maintain a personalized experience.

## Technologies Used

- **Backend**: Flask, SQLite3
- **Frontend**: HTML, CSS, Jinja2 for templating
- **Data Visualization**: Matplotlib, NumPy
- **API Requests**: Flask-RESTful, Requests

## Installation

1. Clone the repository
2. Set up a virtual environment
3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```
5. Run the application:
    ```sh
    python app.py
    ```

## Usage

1. **Registration**: Go to the `/register` route to create a new account.
2. **Login**: Log in using your credentials at the `/login` route.
3. **Dashboard**: Access your portfolio and view ESG scores at the `/dashboard` route.
4. **Search Companies**: Use the `/search` route to find companies and view their ESG scores.
5. **Add/Remove Companies**: Manage your portfolio by adding or removing companies directly from the dashboard.

## API Endpoints

- **User API**:
  - `POST /api/user`: Register a new user.
  - `GET /api/user`: Authenticate an existing user.

- **Portfolio API**:
  - `GET /api/portfolio/<username>`: Get the portfolio for a user.
  - `POST /api/portfolio/<username>/<company_name>`: Add a company to the user's portfolio.
  - `DELETE /api/portfolio/<username>/<company_name>`: Remove a company from the user's portfolio.

- **Graphs API**:
  - `POST /api/graph/<username>`: Generate and save comparison graphs for the user's portfolio.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

This application represents a pivotal tool for modern investors seeking to integrate ESG considerations into their decision-making processes. It facilitates responsible investing practices by offering ESG scorings that foster sustainability and positive societal impact.
