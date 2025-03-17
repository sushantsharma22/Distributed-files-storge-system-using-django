from django.contrib import admin
from .models import StoredFile, FileChunk

@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'owner', 'upload_date', 'file_size', 'checksum')

@admin.register(FileChunk)
class FileChunkAdmin(admin.ModelAdmin):
    list_display = ('stored_file', 'chunk_number', 'file_path', 'checksum', 'replicated')
