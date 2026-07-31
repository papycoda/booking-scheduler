/**
 * Validation utilities for form inputs
 */

export type ValidationError = {
  field: string;
  message: string;
};

export type ValidationResult = {
  valid: boolean;
  errors: ValidationError[];
};

/**
 * Email validation - more thorough than HTML5
 */
export function validateEmail(email: string): ValidationResult {
  const errors: ValidationError[] = [];
  const trimmed = email.trim();

  if (!trimmed) {
    errors.push({ field: "email", message: "Email is required" });
    return { valid: false, errors };
  }

  // Basic format check
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(trimmed)) {
    errors.push({ field: "email", message: "Please enter a valid email address (e.g., name@example.com)" });
  }

  // Check for common typos
  const commonDomains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"];
  const domain = trimmed.split("@")[1]?.toLowerCase();
  if (domain && !commonDomains.includes(domain) && !domain.includes(".")) {
    errors.push({ field: "email", message: "Email domain looks incomplete" });
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Nigerian phone number validation
 * Accepts formats: +234 XXX XXX XXXX or 0XXX XXX XXXX
 * Backend expects only digits (optional +), so we validate the cleaned format
 */
export function validatePhone(phone: string, fieldName: string = "phone"): ValidationResult {
  const errors: ValidationError[] = [];
  const trimmed = phone.trim();

  if (!trimmed) {
    return { valid: true, errors: [] }; // Phone is optional
  }

  // Remove spaces and dashes for validation (backend expects clean format)
  const cleaned = trimmed.replace(/[\s-]/g, "");

  // Backend pattern: ^\+?[0-9]{10,15}$
  // Nigerian phone formats: +234 followed by 10 digits (13 total), or 0 followed by 10 digits (11 total)
  const nigerianPhoneRegex = /^(\+?234|0)[7-9][01]\d{8}$/;
  if (!nigerianPhoneRegex.test(cleaned)) {
    errors.push({
      field: fieldName,
      message: "Please enter a valid Nigerian phone number (e.g., +234 801 234 5678 or 0801 234 5678)"
    });
  }

  // Also check it meets backend's length requirement (10-15 digits, excluding +)
  const digitCount = cleaned.replace(/^\+/, "").length;
  if (digitCount < 10 || digitCount > 15) {
    errors.push({
      field: fieldName,
      message: "Phone number must be between 10 and 15 digits"
    });
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Name validation - should not be empty or just numbers
 */
export function validateName(name: string, fieldName: string = "full_name"): ValidationResult {
  const errors: ValidationError[] = [];
  const trimmed = name.trim();

  if (!trimmed) {
    errors.push({ field: fieldName, message: "Full name is required" });
    return { valid: false, errors };
  }

  if (trimmed.length < 2) {
    errors.push({ field: fieldName, message: "Name must be at least 2 characters" });
  }

  // Check if it's just numbers or special chars
  if (/^[\d\s]+$/.test(trimmed)) {
    errors.push({ field: fieldName, message: "Please enter your actual name" });
  }

  // Max length check
  if (trimmed.length > 255) {
    errors.push({ field: fieldName, message: "Name is too long" });
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Image file validation for inspo images
 */
export function validateInspoImages(files: FileList | null): ValidationResult {
  const errors: ValidationError[] = [];

  if (!files || files.length === 0) {
    return { valid: true, errors: [] }; // Images are optional
  }

  const allowedTypes = ["image/png", "image/jpeg", "image/jpg"];
  const maxSize = 5 * 1024 * 1024; // 5MB

  for (let i = 0; i < files.length; i++) {
    const file = files[i];

    if (!allowedTypes.includes(file.type)) {
      errors.push({
        field: "inspo_images",
        message: `File "${file.name}" must be PNG or JPG format`
      });
    }

    if (file.size > maxSize) {
      errors.push({
        field: "inspo_images",
        message: `File "${file.name}" is too large (max 5MB)`
      });
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Format API error for display
 * Parses backend error responses and returns user-friendly messages
 */
export function formatApiError(error: unknown): string {
  if (typeof error === "string") {
    return error;
  }

  if (error instanceof Error) {
    const message = error.message;
    const apiCode = "code" in error && typeof error.code === "string" ? error.code : "";
    if (apiCode === "VALIDATION_ERROR" && message) {
      return message;
    }

    // Map common error codes to friendly messages
    const errorMappings: Record<string, string> = {
      "TENANT_NOT_FOUND": "This booking page is not available.",
      "SERVICE_NOT_FOUND": "The selected service is not available.",
      "BOOKING_NOT_FOUND": "This booking could not be found.",
      "INSPO_NOT_FOUND": "The inspiration image could not be found.",
      "VALIDATION_ERROR": "Please check your information and try again.",
      "RATE_LIMIT_EXCEEDED": "Too many attempts. Please wait a moment and try again.",
      "SLOT_NOT_AVAILABLE": "This time slot is no longer available. Please choose another.",
      "STAFF_NOT_AVAILABLE": "The selected staff is not available for this service.",
      "PAYSTACK_NOT_CONFIGURED": "Payment is not configured for this environment. Use a demo admin email or add a Paystack test key.",
    };

    for (const [code, friendlyMessage] of Object.entries(errorMappings)) {
      if (message.includes(code) || apiCode === code) {
        return friendlyMessage;
      }
    }

    // Return original message if no mapping found
    return message;
  }

  return "Something went wrong. Please try again.";
}

/**
 * Get field-specific error from validation result
 */
export function getFieldError(validationResult: ValidationResult, fieldName: string): string | null {
  const fieldError = validationResult.errors.find(e => e.field === fieldName);
  return fieldError?.message ?? null;
}
