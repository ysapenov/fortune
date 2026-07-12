"""Entry point for the Job Hunt Helper application."""

import uvicorn


def main():
    """Start the FastAPI application on localhost:8000."""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
