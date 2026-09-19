"""
pdf_to_cbt plugin

Pyrogram plugin that lets users upload coaching-institute test PDFs
(Allen, Aakash, Sarvam, etc.) and receive back a self-contained CBT
(Computer Based Test) HTML file, generated via the Google Gemini API.

This package is discovered automatically by Pyrogram's `plugins/` loader
when the bot's Client is created with `plugins=dict(root="plugins")`.
Nothing in this package creates its own Client or runs the bot -- it only
registers handlers on the existing running Client via decorators.
"""
