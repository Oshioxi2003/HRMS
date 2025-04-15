from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q
import os
import mimetypes
from .models import Document, DocumentCategory
from .forms import DocumentForm, DocumentCategoryForm
from accounts.decorators import check_module_permission, employee_approved_required

@login_required
@employee_approved_required
@check_module_permission('documents', 'Edit')
def document_list(request):
    """List documents based on user's access rights"""
    # Filter by category, search term, etc.
    category_id = request.GET.get('category', '')
    query = request.GET.get('q', '')
    
    # Base query - documents the user can access
    user = request.user
    
    if user.role in ['HR', 'Admin']:
        # HR and Admin can see all documents
        documents = Document.objects.all()
    elif user.role == 'Manager' and user.employee and user.employee.department:
        # Managers can see company documents, department documents for their department,
        # and their own private documents
        department = user.employee.department
        documents = Document.objects.filter(
            Q(visibility='Company') |
            (Q(visibility='Department') & Q(department=department)) |
            (Q(visibility='Private') & Q(uploaded_by=user))
        )
    else:
        # Regular employees can see company documents, their department's documents,
        # and their own private documents
        if user.employee and user.employee.department:
            department = user.employee.department
            documents = Document.objects.filter(
                Q(visibility='Company') |
                (Q(visibility='Department') & Q(department=department)) |
                (Q(visibility='Private') & Q(uploaded_by=user))
            )
        else:
            # Users without an employee profile or department can only see their own documents
            documents = Document.objects.filter(
                Q(visibility='Company') |
                (Q(visibility='Private') & Q(uploaded_by=user))
            )
    
    # Apply filters
    if category_id:
        documents = documents.filter(category_id=category_id)
    
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query)
        )
    
    # Sort by most recent
    documents = documents.order_by('-created_date')
    
    # Paginate results
    paginator = Paginator(documents, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = DocumentCategory.objects.all()
    
    return render(request, 'documents/document_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'query': query
    })

@login_required
@employee_approved_required
@check_module_permission('documents', 'Edit')
def document_upload(request):
    """Upload a new document"""
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            
            # Set file type and size
            uploaded_file = request.FILES['file']
            document.file_type = uploaded_file.content_type
            document.file_size = uploaded_file.size // 1024  # Convert bytes to KB
            
            # Set department if employee has one
            if request.user.employee and request.user.employee.department:
                document.department = request.user.employee.department
            
            document.save()
            messages.success(request, 'Document uploaded successfully')
            return redirect('document_list')
    else:
        form = DocumentForm()
    
    return render(request, 'documents/document_form.html', {'form': form})

@login_required
@employee_approved_required
def document_detail(request, document_id):
    """View document details"""
    document = get_object_or_404(Document, pk=document_id)
    
    # Check if user has access to this document
    user = request.user
    
    if user.role in ['HR', 'Admin']:
        # HR and Admin can access all documents
        pass
    elif document.visibility == 'Company':
        # Company documents are accessible to all users
        pass
    elif document.visibility == 'Department':
        # Department documents require user to be in the same department
        if not user.employee or not user.employee.department or user.employee.department != document.department:
            raise Http404("You don't have permission to access this document")
    elif document.visibility == 'Private':
        # Private documents are only accessible to the uploader
        if document.uploaded_by != user:
            raise Http404("You don't have permission to access this document")
    
    return render(request, 'documents/document_detail.html', {'document': document})

@login_required
@employee_approved_required
def document_download(request, document_id):
    """Download a document"""
    document = get_object_or_404(Document, pk=document_id)
    
    # Check if user has access (similar to detail view)
    user = request.user
    
    if user.role in ['HR', 'Admin']:
        pass
    elif document.visibility == 'Company':
        pass
    elif document.visibility == 'Department':
        if not user.employee or not user.employee.department or user.employee.department != document.department:
            raise Http404("You don't have permission to download this document")
    elif document.visibility == 'Private':
        if document.uploaded_by != user:
            raise Http404("You don't have permission to download this document")
    
    # Prepare file for download
    file_path = document.file.path
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=document.file_type)
            response['Content-Disposition'] = f'attachment; filename="{document.filename()}"'
            return response
    
    raise Http404("Document not found")


@login_required
@employee_approved_required
@check_module_permission('documents', 'Edit')
def document_edit(request, document_id):
    """Edit document details"""
    document = get_object_or_404(Document, pk=document_id)
    
    # Check if user has permission to edit this document
    if not (request.user.role in ['HR', 'Admin'] or document.uploaded_by == request.user):
        messages.error(request, "You don't have permission to edit this document")
        return redirect('document_detail', document_id=document_id)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            # If new file is uploaded, update file type and size
            if 'file' in request.FILES:
                uploaded_file = request.FILES['file']
                document.file_type = uploaded_file.content_type
                document.file_size = uploaded_file.size // 1024  # Convert bytes to KB
            
            form.save()
            messages.success(request, 'Document updated successfully')
            return redirect('document_detail', document_id=document_id)
    else:
        form = DocumentForm(instance=document)
    
    return render(request, 'documents/document_form.html', {
        'form': form,
        'document': document,
        'is_edit': True
    })

@login_required
@employee_approved_required
@check_module_permission('documents', 'Delete')
def document_delete(request, document_id):
    """Delete a document"""
    document = get_object_or_404(Document, pk=document_id)
    
    # Check if user has permission to delete this document
    if not (request.user.role in ['HR', 'Admin'] or document.uploaded_by == request.user):
        messages.error(request, "You don't have permission to delete this document")
        return redirect('document_detail', document_id=document_id)
    
    if request.method == 'POST':
        # Delete the file from storage
        if document.file:
            if os.path.isfile(document.file.path):
                os.remove(document.file.path)
        
        document.delete()
        messages.success(request, 'Document deleted successfully')
        return redirect('document_list')
    
    return render(request, 'documents/document_confirm_delete.html', {'document': document})

@login_required
@employee_approved_required
@check_module_permission('documents', 'View')
def document_category_list(request):
    """List all document categories"""
    categories = DocumentCategory.objects.all().order_by('category_name')
    
    # Add document count for each category
    for category in categories:
        category.document_count = Document.objects.filter(category=category).count()
    
    return render(request, 'documents/category_list.html', {'categories': categories})

@login_required
@employee_approved_required
@check_module_permission('documents', 'Edit')
def document_category_create(request):
    """Create a new document category"""
    if request.method == 'POST':
        form = DocumentCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully')
            return redirect('document_category_list')
    else:
        form = DocumentCategoryForm()
    
    return render(request, 'documents/category_form.html', {'form': form})

@login_required
@employee_approved_required
@check_module_permission('documents', 'Edit')
def document_category_edit(request, category_id):
    """Edit a document category"""
    category = get_object_or_404(DocumentCategory, pk=category_id)
    
    if request.method == 'POST':
        form = DocumentCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully')
            return redirect('document_category_list')
    else:
        form = DocumentCategoryForm(instance=category)
    
    return render(request, 'documents/category_form.html', {
        'form': form,
        'category': category,
        'is_edit': True
    })

@login_required
@employee_approved_required
@check_module_permission('documents', 'Delete')
def document_category_delete(request, category_id):
    """Delete a document category"""
    category = get_object_or_404(DocumentCategory, pk=category_id)
    
    # Check if there are documents using this category
    document_count = Document.objects.filter(category=category).count()
    
    if request.method == 'POST':
        if document_count > 0:
            messages.error(request, f'Cannot delete category "{category.category_name}" because it is used by {document_count} documents')
            return redirect('document_category_list')
        
        category.delete()
        messages.success(request, 'Category deleted successfully')
        return redirect('document_category_list')
    
    return render(request, 'documents/category_confirm_delete.html', {
        'category': category,
        'document_count': document_count
    })

@login_required
@employee_approved_required
def my_documents(request):
    """View documents uploaded by the current user"""
    documents = Document.objects.filter(uploaded_by=request.user).order_by('-created_date')
    
    # Filter by category if provided
    category_id = request.GET.get('category', '')
    if category_id:
        documents = documents.filter(category_id=category_id)
    
    # Paginate results
    paginator = Paginator(documents, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = DocumentCategory.objects.all()
    
    return render(request, 'documents/my_documents.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_id
    })

@login_required
@employee_approved_required
def department_documents(request):
    """View documents for the user's department"""
    user = request.user
    
    # Check if user has a department
    if not user.employee or not user.employee.department:
        messages.warning(request, "You are not associated with any department")
        return redirect('document_list')
    
    department = user.employee.department
    
    # Get documents visible to the department
    documents = Document.objects.filter(
        Q(visibility='Department', department=department) |
        Q(visibility='Company')
    ).order_by('-created_date')
    
    # Filter by category if provided
    category_id = request.GET.get('category', '')
    if category_id:
        documents = documents.filter(category_id=category_id)
    
    # Paginate results
    paginator = Paginator(documents, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = DocumentCategory.objects.all()
    
    return render(request, 'documents/department_documents.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'department': department
    })

@login_required
@employee_approved_required
def document_search(request):
    """Search for documents"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    visibility = request.GET.get('visibility', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base query - documents the user can access
    user = request.user
    
    if user.role in ['HR', 'Admin']:
        # HR and Admin can see all documents
        documents = Document.objects.all()
    elif user.role == 'Manager' and user.employee and user.employee.department:
        # Managers can see company documents, department documents for their department,
        # and their own private documents
        department = user.employee.department
        documents = Document.objects.filter(
            Q(visibility='Company') |
            (Q(visibility='Department') & Q(department=department)) |
            (Q(visibility='Private') & Q(uploaded_by=user))
        )
    else:
        # Regular employees can see company documents, their department's documents,
        # and their own private documents
        if user.employee and user.employee.department:
            department = user.employee.department
            documents = Document.objects.filter(
                Q(visibility='Company') |
                (Q(visibility='Department') & Q(department=department)) |
                (Q(visibility='Private') & Q(uploaded_by=user))
            )
        else:
            # Users without an employee profile or department can only see their own documents
            documents = Document.objects.filter(
                Q(visibility='Company') |
                (Q(visibility='Private') & Q(uploaded_by=user))
            )
    
    # Apply search filters
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query)
        )
    
    if category_id:
        documents = documents.filter(category_id=category_id)
    
    if visibility:
        documents = documents.filter(visibility=visibility)
    
    if date_from:
        documents = documents.filter(created_date__gte=date_from)
    
    if date_to:
        documents = documents.filter(created_date__lte=date_to)
    
    # Sort by most recent
    documents = documents.order_by('-created_date')
    
    # Paginate results
    paginator = Paginator(documents, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = DocumentCategory.objects.all()
    
    return render(request, 'documents/document_search.html', {
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category_id,
        'query': query,
        'visibility': visibility,
        'date_from': date_from,
        'date_to': date_to
    })
