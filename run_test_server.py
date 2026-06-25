"""Run Flask app on port 5678 for testing."""
import app as myapp
myapp.app.run(port=5678, debug=False)
