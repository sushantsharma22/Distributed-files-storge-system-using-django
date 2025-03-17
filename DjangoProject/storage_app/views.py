import os
import hashlib
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import FileUploadForm
from .models import StoredFile, FileChunk

# Define simulated node directories
NODE_DIRS = [
    os.path.join(settings.MEDIA_ROOT, 'nodes', 'node1'),
    os.path.join(settings.MEDIA_ROOT, 'nodes', 'node2'),
    os.path.join(settings.MEDIA_ROOT, 'nodes', 'node3'),
]

# Ensure that node directories exist
for node in NODE_DIRS:
    os.makedirs(node, exist_ok=True)

CHUNK_SIZE = 1024 * 1024  # 1 MB chunk size

def calculate_checksum(file_obj):
    sha256 = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256.update(chunk)
    return sha256.hexdigest()

def chunk_file(file_obj, chunk_size=CHUNK_SIZE):
    while True:
        data = file_obj.read(chunk_size)
        if not data:
            break
        yield data

def get_node_from_path(file_path):
    parts = file_path.split('nodes/')
    if len(parts) > 1:
        node_subpath = parts[1]  # e.g. "node1/filename"
        return node_subpath.split('/')[0]
    return 'Unknown'

def get_node_load(node_name):
    # Count primary chunks (replicated=False) stored in a given node
    return FileChunk.objects.filter(file_path__icontains=f"/nodes/{node_name}/", replicated=False).count()

@login_required
def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            overall_checksum = calculate_checksum(uploaded_file)
            uploaded_file.seek(0)
            # Deduplication: If a file with the same checksum exists, skip re-uploading chunks.
            existing_file = StoredFile.objects.filter(checksum=overall_checksum).first()
            if existing_file:
                # Optionally, you could add the current user to a ManyToMany field here.
                return redirect('file_list')
            stored_file = StoredFile.objects.create(
                file_name=uploaded_file.name,
                owner=request.user,
                file_size=uploaded_file.size,
                checksum=overall_checksum
            )
            chunk_number = 0
            node_index = 0
            for chunk in chunk_file(uploaded_file):
                chunk_checksum = hashlib.sha256(chunk).hexdigest()
                # Choose primary node via round-robin
                primary_node_path = NODE_DIRS[node_index % len(NODE_DIRS)]
                node_index += 1
                chunk_filename = f"{stored_file.id}_chunk_{chunk_number}"
                primary_full_path = os.path.join(primary_node_path, chunk_filename)
                with open(primary_full_path, 'wb') as f:
                    f.write(chunk)
                FileChunk.objects.create(
                    stored_file=stored_file,
                    chunk_number=chunk_number,
                    file_path=primary_full_path,
                    checksum=chunk_checksum,
                    replicated=False
                )
                # Replicate the chunk to the next node in line
                replicate_node_path = NODE_DIRS[node_index % len(NODE_DIRS)]
                replicate_full_path = os.path.join(replicate_node_path, chunk_filename + '_replica')
                with open(replicate_full_path, 'wb') as f:
                    f.write(chunk)
                FileChunk.objects.create(
                    stored_file=stored_file,
                    chunk_number=chunk_number,
                    file_path=replicate_full_path,
                    checksum=chunk_checksum,
                    replicated=True
                )
                chunk_number += 1
            return redirect('file_list')
    else:
        form = FileUploadForm()
    return render(request, 'storage_app/upload.html', {'form': form})

@login_required
def file_list(request):
    files = StoredFile.objects.all().order_by('-upload_date')
    return render(request, 'storage_app/list_files.html', {'files': files})

@login_required
def download_file(request, file_id):
    stored_file = get_object_or_404(StoredFile, pk=file_id)
    file_data = b""

    # Get all primary chunks (replicated=False) in ascending order
    primary_chunks = stored_file.chunks.filter(replicated=False).order_by('chunk_number')

    for primary_chunk in primary_chunks:
        # Gather both primary and replica chunk records for this chunk_number
        chunk_candidates = stored_file.chunks.filter(chunk_number=primary_chunk.chunk_number)
        valid_candidates = []

        # Check each candidate to see if it exists on disk and passes checksum
        for candidate in chunk_candidates:
            if os.path.exists(candidate.file_path):
                with open(candidate.file_path, 'rb') as f:
                    data = f.read()
                    if hashlib.sha256(data).hexdigest() == candidate.checksum:
                        # This candidate chunk is valid
                        valid_candidates.append((candidate, data))

        # If no valid copy of this chunk was found, return an error response
        if not valid_candidates:
            return HttpResponse(
                f"Error: Missing or corrupted chunk #{primary_chunk.chunk_number}. "
                f"Cannot reconstruct file '{stored_file.file_name}'.",
                status=500
            )

        # If we do have valid candidates, pick the one from the least-loaded node
        selected_candidate, selected_data = valid_candidates[0]
        selected_node = get_node_from_path(selected_candidate.file_path)
        selected_load = get_node_load(selected_node)

        for candidate, data in valid_candidates[1:]:
            candidate_node = get_node_from_path(candidate.file_path)
            candidate_load = get_node_load(candidate_node)
            if candidate_load < selected_load:
                selected_candidate, selected_data = candidate, data
                selected_load = candidate_load

        # Append the chosen chunk’s data to the final file
        file_data += selected_data

    # If we reach here, all chunks were found and reassembled successfully
    response = HttpResponse(file_data, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{stored_file.file_name}"'
    return response

@login_required
def dashboard(request):
    node_chunks = defaultdict(list)
    all_chunks = FileChunk.objects.select_related('stored_file').all()
    for chunk in all_chunks:
        node_name = get_node_from_path(chunk.file_path)
        node_chunks[node_name].append(chunk)
    context = {'node_chunks': dict(node_chunks)}
    return render(request, 'storage_app/dashboard.html', context)
