from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.utils.translation import gettext as _
from accounts.decorators import check_module_permission

import os
import mimetypes
from datetime import datetime

from .models import Employee, EmployeeDocument

@login_required
@check_module_permission('employee', 'View')
def employee_documents(request, employee_id):
    """View all documents for an employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    documents = EmployeeDocument.objects.filter(employee=employee).order_by('-uploaded_date')
    
    context = {
        'employee': employee,
        'documents': documents,
        'document_types': EmployeeDocument.DOCUMENT_TYPES
    }
    
    return render(request, 'employee/employee_documents.html', context)

@login_required
@check_module_permission('employee', 'Edit')
def upload_document(request, employee_id):
    """Upload a new document for an employee"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    if request.method == 'POST':
        document_type = request.POST.get('document_type')
        description = request.POST.get('description', '')
        
        if 'document_file' in request.FILES:
            uploaded_file = request.FILES['document_file']
            
            # Create document record
            document = EmployeeDocument(
                employee=employee,
                document_type=document_type,
                file=uploaded_file,
                file_name=uploaded_file.name,
                file_type=uploaded_file.content_type,
                file_size=uploaded_file.size // 1024,  # Convert bytes to KB
                description=description
            )
            document.save()
            
            messages.success(request, _('Document uploaded successfully.'))
            return redirect('employee_documents', employee_id=employee_id)
        else:
            messages.error(request, _('No file was uploaded.'))
    
    return redirect('employee_documents', employee_id=employee_id)

@login_required
@check_module_permission('employee', 'View')
def view_document(request, document_id):
    """View/download a document"""
    document = get_object_or_404(EmployeeDocument, pk=document_id)
    
    # Security check - ensure user has permission to view this employee's documents
    if not request.user.is_staff and not request.user.is_superuser:
        if hasattr(request.user, 'employee') and request.user.employee != document.employee:
            messages.error(request, _('You do not have permission to view this document.'))
            return redirect('dashboard')
    
    # Get the file path
    file_path = os.path.join(settings.MEDIA_ROOT, str(document.file))
    
    # Check if file exists
    if not os.path.exists(file_path):
        messages.error(request, _('Document file not found.'))
        return redirect('employee_documents', employee_id=document.employee.employee_id)
    
    # Log the document view
    if hasattr(request, 'user') and request.user.is_authenticated:
        from accounts.models import SystemLog
        SystemLog.objects.create(
            user=request.user,
            action="Document View",
            object_type="EmployeeDocument",
            object_id=document.document_id,
            details=f"Viewed {document.get_document_type_display()} for {document.employee.full_name}"
        )
    
    # Determine if it's a viewable file or should be downloaded
    content_type, encoding = mimetypes.guess_type(file_path)
    if content_type and content_type.startswith(('image/', 'application/pdf')):
        # For images and PDFs - can be viewed in browser
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type=content_type)
            response['Content-Disposition'] = f'inline; filename="{document.file_name}"'
            return response
    else:
        # For other files - force download
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
            return response

@login_required
@check_module_permission('employee', 'Delete')
def delete_document(request, document_id):
    """Delete a document"""
    document = get_object_or_404(EmployeeDocument, pk=document_id)
    employee_id = document.employee.employee_id
    
    if request.method == 'POST':
        # Store document information for logging
        doc_type = document.get_document_type_display()
        employee_name = document.employee.full_name
        
        # Get the file path to delete the file from storage
        file_path = os.path.join(settings.MEDIA_ROOT, str(document.file))
        
        # Delete the document record from the database
        document.delete()
        
        # Delete the actual file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Log the document deletion
        if hasattr(request, 'user') and request.user.is_authenticated:
            from accounts.models import SystemLog
            SystemLog.objects.create(
                user=request.user,
                action="Document Delete",
                object_type="EmployeeDocument",
                details=f"Deleted {doc_type} for {employee_name}"
            )
        
        messages.success(request, _('Document deleted successfully.'))
        return redirect('employee_documents', employee_id=employee_id)
    
    context = {
        'document': document,
        'employee': document.employee
    }
    
    return render(request, 'employee/document_confirm_delete.html', context)
