rcl_form_schema = {
    "title": "Reduced Course Load (RCL) Form",
    "description": "Form for requesting reduced course load for graduate students",
    "type": "object",
    "sections": [
        {
            "id": "academic_difficulty",
            "title": "1. ACADEMIC DIFFICULTY (FIRST SEMESTER ONLY)",
            "description": "RCL for valid academic difficulties is allowed once and only in the first semester when starting a new degree program. A minimum of 6hrs will still have to completed. This option cannot be used or submitted prior to ORD",
            "fields": [
                {
                    "id": "iai",
                    "title": "Initial Adjustment Issues (IAI)",
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["english", "reading", "teaching"]
                    },
                    "uniqueItems": True
                },
                {
                    "id": "iclp",
                    "title": "Improper Course Level Placement (ICLP)",
                    "type": "boolean",
                    "default": False
                }
            ]
        },
        {
            "id": "medical_reason",
            "title": "2. MEDICAL REASON",
            "fields": [
                {
                    "id": "medical",
                    "title": "Medical Reason",
                    "type": "boolean",
                    "default": False
                },
                {
                    "id": "letter_attached",
                    "title": "Letter from licensed medical professional is attached",
                    "type": "boolean",
                    "default": False
                }
            ]
        },
        {
            "id": "final_semester",
            "title": "3. FULL-TIME EQUIVALENCE FOR FINAL SEMESTER",
            "fields": [
                {
                    "id": "track",
                    "title": "Track Selection",
                    "type": "string",
                    "enum": ["non_thesis", "thesis"]
                },
                {
                    "id": "non_thesis_hours",
                    "title": "Hours needed for Non-Thesis Track",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                    "conditional": {
                        "field": "track",
                        "value": "non_thesis"
                    }
                },
                {
                    "id": "thesis_hours",
                    "title": "Hours needed for Thesis Track",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                    "conditional": {
                        "field": "track",
                        "value": "thesis"
                    }
                }
            ]
        },
        {
            "id": "semester_info",
            "title": "Semester Information",
            "fields": [
                {
                    "id": "semester",
                    "title": "Semester",
                    "type": "string",
                    "enum": ["fall", "spring"]
                },
                {
                    "id": "fall_year",
                    "title": "Fall Year",
                    "type": "string",
                    "pattern": "^[0-9]{2}$",
                    "conditional": {
                        "field": "semester",
                        "value": "fall"
                    }
                },
                {
                    "id": "spring_year",
                    "title": "Spring Year",
                    "type": "string",
                    "pattern": "^[0-9]{2}$",
                    "conditional": {
                        "field": "semester",
                        "value": "spring"
                    }
                },
                {
                    "id": "course1",
                    "title": "Course 1 to drop",
                    "type": "string"
                },
                {
                    "id": "course2",
                    "title": "Course 2 to drop",
                    "type": "string"
                },
                {
                    "id": "course3",
                    "title": "Course 3 to drop",
                    "type": "string"
                },
                {
                    "id": "remaining_hours",
                    "title": "Remaining hours after drop",
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 9
                }
            ]
        },
        {
            "id": "student_info",
            "title": "Student Information",
            "fields": [
                {
                    "id": "name",
                    "title": "Student Name",
                    "type": "string"
                },
                {
                    "id": "ps_id",
                    "title": "PS ID",
                    "type": "string",
                    "required": True
                },
                {
                    "id": "signature_date",
                    "title": "Date",
                    "type": "string",
                    "format": "date",
                    "required": True
                }
            ]
        }
    ],
    "required": ["student_info"]
}


withdrawal_form_schema = {
                "title": "Medical/Administrative Term Withdrawal Request Form",
                "description": "Form for requesting withdrawal from all courses for a specific term",
                "type": "object",
                "sections": [
                    {
                        "id": "student_information",
                        "title": "STUDENT INFORMATION",
                        "fields": [
                            {
                                "id": "myUHID",
                                "title": "myUH ID",
                                "type": "string",
                                "required": True
                            },
                            {
                                "id": "college",
                                "title": "College",
                                "type": "string"
                            },
                            {
                                "id": "planDegree",
                                "title": "Plan/Degree",
                                "type": "string"
                            },
                            {
                                "id": "address",
                                "title": "Current Mailing Address",
                                "type": "string"
                            },
                            {
                                "id": "phoneNumber",
                                "title": "Phone Number",
                                "type": "string"
                            }
                        ]
                    },
                    {
                        "id": "withdrawal_details",
                        "title": "WITHDRAWAL DETAILS",
                        "fields": [
                            {
                                "id": "termYear",
                                "title": "Term for withdrawal",
                                "type": "string",
                                "required": True
                            },
                            {
                                "id": "reason",
                                "title": "Reason for Request",
                                "type": "string",
                                "required": True
                            },
                            {
                                "id": "lastDateAttended",
                                "title": "Last Date Attended Classes",
                                "type": "string",
                                "format": "date"
                            },
                            {
                                "id": "financialAssistance",
                                "title": "Received financial assistance?",
                                "type": "boolean",
                                "default": False
                            },
                            {
                                "id": "studentHealthInsurance",
                                "title": "Have UH student health insurance?",
                                "type": "boolean",
                                "default": False
                            },
                            {
                                "id": "campusHousing",
                                "title": "Live in campus housing?",
                                "type": "boolean",
                                "default": False
                            },
                            {
                                "id": "visaStatus",
                                "title": "Hold F1 or J1 Visa?",
                                "type": "boolean",
                                "default": False
                            },
                            {
                                "id": "giBillBenefits",
                                "title": "Using G.I. Bill benefits?",
                                "type": "boolean",
                                "default": False
                            }
                        ]
                    },
                    {
                        "id": "withdrawal_type",
                        "title": "Type of Withdrawal",
                        "fields": [
                            {
                                "id": "withdrawalType",
                                "title": "Withdrawal Type",
                                "type": "string",
                                "enum": ["medical", "administrative"],
                                "required": True
                            }
                        ]
                    },
                    {
                        "id": "courses",
                        "title": "Courses to Withdraw",
                        "fields": [
                            {
                                "id": "coursesToWithdraw",
                                "title": "List all courses and sections",
                                "type": "string"
                            }
                        ]
                    },
                    {
                        "id": "comments",
                        "title": "Additional Comments",
                        "fields": [
                            {
                                "id": "additionalComments",
                                "title": "Additional Comments",
                                "type": "string"
                            }
                        ]
                    }
                ],
                "required": ["student_information", "withdrawal_details", "withdrawal_type"]
            }