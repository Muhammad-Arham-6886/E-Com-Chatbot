import io
import os
import zipfile
from app.models.website import Website


class WordPressPluginService:
    PLUGIN_ROOT = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "wordpress-plugin",
            "ai-commerce-assistant",
        )
    )

    @classmethod
    def generate_plugin_zip(cls, website: Website, api_url: str = "http://localhost:8000") -> bytes:
        """
        Dynamically packages the WordPress plugin into a zip archive with
        the website's public_site_id and api_url pre-configured as activation defaults.
        """
        buffer = io.BytesIO()
        clean_api_url = api_url.rstrip("/")

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Walk the plugin template directory if it exists
            if os.path.exists(cls.PLUGIN_ROOT):
                for root, _, files in os.walk(cls.PLUGIN_ROOT):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, os.path.dirname(cls.PLUGIN_ROOT))
                        
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        # In the main plugin file, inject the website's default configuration
                        if file == "ai-commerce-assistant.php":
                            activation_snippet = (
                                f"    update_option('ai_commerce_public_site_id', '{website.public_site_id}');\n"
                                f"    update_option('ai_commerce_api_url', '{clean_api_url}');\n"
                                "    update_option('ai_commerce_enabled', 'yes');\n"
                            )
                            content = content.replace(
                                "    if (!get_option('ai_commerce_api_url')) {\n"
                                "        update_option('ai_commerce_api_url', 'http://localhost:8000');\n"
                                "    }",
                                activation_snippet,
                            )

                        zip_file.writestr(rel_path.replace("\\", "/"), content)
            else:
                # Fallback: create standalone minimal plugin if template dir is missing
                main_php = f"""<?php
/**
 * Plugin Name: AI Customer & Commerce Assistant
 * Version: 1.0.0
 * Description: Pre-configured for {website.name} ({website.domain})
 */
add_action('wp_footer', function() {{
    echo '<script src="{clean_api_url}/static/widget.js" data-site-id="{website.public_site_id}" data-api-url="{clean_api_url}" async></script>';
}});
"""
                zip_file.writestr("ai-commerce-assistant/ai-commerce-assistant.php", main_php)

        buffer.seek(0)
        return buffer.getvalue()
