#!/usr/bin/env python3
"""
Wegmans Shopping App - Simple Web Server

Just starts the web server on configured port.
Visit http://localhost:{port} after starting.
"""

import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import asyncio
from dotenv import load_dotenv
from src.scraper.wegmans_scraper import WegmansScraper
from config.settings import settings

# Load environment variables from .env file
load_dotenv()


class WegmansServer(SimpleHTTPRequestHandler):
    """Simple HTTP server for Wegmans shopping app"""

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('frontend/index.html', 'rb') as f:
                self.wfile.write(f.read())

        elif self.path.startswith('/css/'):
            # Serve CSS files
            try:
                self.send_response(200)
                self.send_header('Content-type', 'text/css')
                self.end_headers()
                css_file = 'frontend' + self.path
                with open(css_file, 'rb') as f:
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()

        elif self.path.startswith('/js/'):
            # Serve JavaScript files
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/javascript')
                self.end_headers()
                js_file = 'frontend' + self.path
                with open(js_file, 'rb') as f:
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()

        elif self.path == '/cart.json':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                cart_file = settings.USER_DATA_DIR / 'cart.json'
                with open(cart_file, 'rb') as f:
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'[]')

        else:
            super().do_GET()

    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/save_cart':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            cart_file = settings.USER_DATA_DIR / 'cart.json'
            with open(cart_file, 'wb') as f:
                f.write(post_data)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "saved"}')

        elif self.path == '/search':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)

                search_term = data.get('search_term', '')

                if not search_term:
                    self.send_response(400)
                    self.end_headers()
                    return

                # Run async search
                import nest_asyncio
                nest_asyncio.apply()

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(self._do_search(search_term))
                loop.close()

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(results).encode())

            except Exception as e:
                print(f"Search error: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

    async def _do_search(self, search_term):
        """Search Wegmans for products"""
        print(f"🔍 Searching for: {search_term}")
        async with WegmansScraper(
            headless=settings.SCRAPER_HEADLESS,
            store_location=settings.STORE_LOCATION
        ) as scraper:
            products = await scraper.search_products(
                search_term,
                max_results=settings.SEARCH_MAX_RESULTS
            )
            return products


if __name__ == "__main__":
    try:
        server = HTTPServer((settings.HOST, settings.PORT), WegmansServer)
        print("\n" + "=" * 60)
        print("🛒 Wegmans Shopping App - Web Server")
        print("=" * 60)
        print(f"\n📱 Open in your browser:")
        print(f"   http://{settings.HOST}:{settings.PORT}")
        print(f"\n⚙️  Store: {settings.STORE_LOCATION}")
        print("\n⌨️  Press Ctrl+C to stop")
        print("=" * 60)
        print()
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
        sys.exit(0)
    except OSError as e:
        if 'Address already in use' in str(e):
            print(f"\n❌ Error: Port {settings.PORT} is already in use")
            print(f"   Kill it with: lsof -ti:{settings.PORT} | xargs kill -9")
        else:
            raise
