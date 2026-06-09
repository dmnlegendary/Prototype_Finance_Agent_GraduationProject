# Intelligent Virtual Assistant & POS System for Microenterprises 🛒🧠

A prototype point-of-sale (POS) and inventory management system designed specifically for miscellaneous stores in Mexico City. Developed as an engineering graduation project, this system features a cloud-oriented architecture, integrating Machine Learning for demand forecasting and a text-based AI virtual assistant to empower business owners with data-driven insights.

## 📖 Project Overview

Small retail businesses often lack the hardware budget and technical expertise required to run complex enterprise resource planning (ERP) software. This project solves that gap by providing a robust, lightweight, and highly accessible management system. 

Designed around a **Thin-Client Architecture**, the system is structured to offload heavy computational lifting—including predictive analytics and LLM reasoning—to backend servers and external APIs. While currently operating as a local prototype, this architectural foundation ensures that upon future cloud deployment, store owners will be able to operate the system fluently on existing low-end hardware (basic tablets, smartphones, or older desktop computers) with minimal internet bandwidth.

## ✨ Core Features

* **Transactional POS & Inventory Engine:** A strictly ACID-compliant module handling sales, inventory deduction, and financial tracking in real-time.
* **Predictive Demand Forecasting (ML):** Utilizes historical sales data and Machine Learning algorithms to predict future product demand, helping owners optimize stock levels and reduce waste.
* **Text-Based AI Financial Assistant:** A secure, read-only conversational agent powered by Large Language Models (LLMs). Store owners can ask text-based questions in natural language (e.g., *"Which products are expiring next week?"* or *"What were the top-selling items yesterday?"*), and the assistant returns structured, accurate business insights.
* **Zero Local NLP Overhead:** To guarantee performance on low-resource devices, voice command processing and local Natural Language Processing have been intentionally excluded by design.

## 🏗️ System Architecture

The project follows a **Client-Server** architecture, internally structured using the **Model-Template-View (MTV)** pattern.

1.  **Presentation Layer (Frontend):** Built with HTML5, CSS3 (Bootstrap 5), and vanilla JavaScript (ES6). Uses the Fetch API for asynchronous communication, ensuring a seamless Single Page Application (SPA) feel without heavy frameworks.
2.  **Business Logic (Backend):** Powered by Python and Django, acting as the central orchestrator handling route protection, data validation, and database operations.
3.  **Data Persistence:** SQL-based relational database for structured storage of product catalogs and transactions.
4.  **External Services (RESTful API Bridge):** Secure, HTTPS-encrypted communication with LLM providers. The backend sanitizes prompts, manages context windows (to minimize token costs), and extracts intelligent responses without exposing API keys to the client side.

## 💻 Technology Stack

* **Backend:** Python 3.12, Django 5.x
* **Frontend:** HTML5, CSS3, JavaScript ES6+, Bootstrap 5
* **Database:** SQL
* **AI/ML:** Machine Learning libraries like scikit-learn or keras, including the use of API's for a LLM agent integration
* **Deployment Roadmap:** Currently a local prototype, architecturally prepared for future cloud deployment (e.g., Microsoft Azure App Service).

## 🔒 Security & Optimization

* **Prompt Injection Protection:** The AI assistant operates strictly with read-only permissions over the database. Input sanitization prevents malicious command execution.
* **Token & Context Management:** The system automatically truncates chat histories, ensuring lightweight API payloads to maintain sub-second latency and control operational costs.
* **Secure Sessions:** Session management relies on server-side tokens and HTTPS encryption, mitigating local credential exposure.

## 👥 Authors
* **Jorge Arif Diaz Jimenez** - *Artificial Intelligence Engineering*
* **Bernardo** - *Artificial Intelligence Engineering*

*Developed at the Escuela Superior de Cómputo (ESCOM) - Instituto Politécnico Nacional (IPN).*
