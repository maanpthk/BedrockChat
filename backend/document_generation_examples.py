"""
Example prompts and expected outputs for document generation tools.
These examples show how users can interact with the document generation tools through natural language.
"""

EXAMPLE_PROMPTS = {
    "powerpoint": [
        {
            "user_prompt": "Create a presentation about artificial intelligence with 4 slides covering introduction, applications, benefits, and future trends",
            "expected_tool_call": {
                "tool": "generate_powerpoint",
                "args": {
                    "title": "Artificial Intelligence Overview",
                    "slides": [
                        {
                            "title": "Introduction to AI",
                            "content": "Artificial Intelligence (AI) refers to computer systems that can perform tasks typically requiring human intelligence."
                        },
                        {
                            "title": "AI Applications",
                            "bullet_points": [
                                "Healthcare and medical diagnosis",
                                "Autonomous vehicles and transportation",
                                "Natural language processing",
                                "Computer vision and image recognition",
                                "Financial analysis and trading"
                            ]
                        },
                        {
                            "title": "Benefits of AI",
                            "bullet_points": [
                                "Increased efficiency and productivity",
                                "24/7 availability and consistency",
                                "Data-driven decision making",
                                "Automation of repetitive tasks",
                                "Enhanced accuracy and precision"
                            ]
                        },
                        {
                            "title": "Future Trends",
                            "bullet_points": [
                                "Generative AI and large language models",
                                "AI integration in everyday applications",
                                "Ethical AI and responsible development",
                                "Edge AI and mobile computing",
                                "AI-human collaboration"
                            ]
                        }
                    ],
                    "theme_color": "blue"
                }
            }
        },
        {
            "user_prompt": "Make a quarterly business review presentation with executive summary, financial performance, key achievements, and next quarter goals",
            "expected_tool_call": {
                "tool": "generate_powerpoint",
                "args": {
                    "title": "Q1 2024 Business Review",
                    "slides": [
                        {
                            "title": "Executive Summary",
                            "content": "Q1 2024 demonstrated strong performance across all key metrics with revenue growth of 15% and successful product launches."
                        },
                        {
                            "title": "Financial Performance",
                            "bullet_points": [
                                "Revenue: $2.5M (15% increase YoY)",
                                "Gross margin: 68% (up from 65%)",
                                "Operating expenses: $1.2M",
                                "Net profit: $450K (25% increase)",
                                "Cash flow: Positive $380K"
                            ]
                        },
                        {
                            "title": "Key Achievements",
                            "bullet_points": [
                                "Launched new product line successfully",
                                "Expanded to 3 new markets",
                                "Increased customer base by 30%",
                                "Improved customer satisfaction to 94%",
                                "Completed digital transformation initiative"
                            ]
                        },
                        {
                            "title": "Q2 2024 Goals",
                            "bullet_points": [
                                "Target 20% revenue growth",
                                "Launch mobile application",
                                "Expand team by 15 people",
                                "Enter European market",
                                "Implement AI-powered analytics"
                            ]
                        }
                    ],
                    "theme_color": "green"
                }
            }
        }
    ],
    
    "word_document": [
        {
            "user_prompt": "Create a project proposal document for a new mobile app with sections for overview, objectives, timeline, budget, and team",
            "expected_tool_call": {
                "tool": "generate_word_document",
                "args": {
                    "title": "Mobile App Development Project Proposal",
                    "content": [
                        {
                            "type": "heading",
                            "text": "Project Overview",
                            "level": 1
                        },
                        {
                            "type": "paragraph",
                            "text": "This proposal outlines the development of a new mobile application designed to enhance customer engagement and streamline business operations. The app will provide users with intuitive access to our services while incorporating modern design principles and cutting-edge technology."
                        },
                        {
                            "type": "heading",
                            "text": "Project Objectives",
                            "level": 1
                        },
                        {
                            "type": "bullet_list",
                            "items": [
                                "Develop a cross-platform mobile application for iOS and Android",
                                "Improve customer engagement by 40%",
                                "Reduce customer service inquiries by 25%",
                                "Increase mobile revenue by 60%",
                                "Enhance brand visibility and market presence"
                            ]
                        },
                        {
                            "type": "heading",
                            "text": "Project Timeline",
                            "level": 1
                        },
                        {
                            "type": "numbered_list",
                            "items": [
                                "Phase 1: Requirements gathering and design (4 weeks)",
                                "Phase 2: Development and testing (12 weeks)",
                                "Phase 3: Beta testing and feedback (3 weeks)",
                                "Phase 4: Launch and deployment (2 weeks)",
                                "Phase 5: Post-launch support and optimization (ongoing)"
                            ]
                        },
                        {
                            "type": "heading",
                            "text": "Budget Estimate",
                            "level": 1
                        },
                        {
                            "type": "paragraph",
                            "text": "The total project budget is estimated at $150,000, broken down into development costs ($100,000), design and UX ($25,000), testing and QA ($15,000), and project management ($10,000). This includes all necessary resources, tools, and third-party integrations."
                        },
                        {
                            "type": "heading",
                            "text": "Project Team",
                            "level": 1
                        },
                        {
                            "type": "bullet_list",
                            "items": [
                                "Project Manager: Sarah Johnson",
                                "Lead Developer: Michael Chen",
                                "UI/UX Designer: Emily Rodriguez",
                                "QA Engineer: David Kim",
                                "Backend Developer: Alex Thompson"
                            ]
                        }
                    ],
                    "font_size": 12
                }
            }
        },
        {
            "user_prompt": "Write a technical documentation for our API with introduction, authentication, endpoints, and examples",
            "expected_tool_call": {
                "tool": "generate_word_document",
                "args": {
                    "title": "API Technical Documentation",
                    "content": [
                        {
                            "type": "heading",
                            "text": "Introduction",
                            "level": 1
                        },
                        {
                            "type": "paragraph",
                            "text": "This document provides comprehensive technical documentation for our REST API. The API enables developers to integrate with our platform and access core functionality programmatically. All endpoints return JSON responses and follow RESTful conventions."
                        },
                        {
                            "type": "heading",
                            "text": "Authentication",
                            "level": 1
                        },
                        {
                            "type": "paragraph",
                            "text": "The API uses Bearer token authentication. Include your API key in the Authorization header for all requests."
                        },
                        {
                            "type": "heading",
                            "text": "Base URL",
                            "level": 2
                        },
                        {
                            "type": "paragraph",
                            "text": "https://api.example.com/v1"
                        },
                        {
                            "type": "heading",
                            "text": "Available Endpoints",
                            "level": 1
                        },
                        {
                            "type": "bullet_list",
                            "items": [
                                "GET /users - Retrieve user list",
                                "POST /users - Create new user",
                                "GET /users/{id} - Get user by ID",
                                "PUT /users/{id} - Update user",
                                "DELETE /users/{id} - Delete user",
                                "GET /projects - List all projects",
                                "POST /projects - Create new project"
                            ]
                        },
                        {
                            "type": "heading",
                            "text": "Request Examples",
                            "level": 1
                        },
                        {
                            "type": "paragraph",
                            "text": "Example request to create a new user: POST /users with JSON payload containing name, email, and role fields. The response will include the created user object with assigned ID and timestamps."
                        },
                        {
                            "type": "heading",
                            "text": "Error Handling",
                            "level": 1
                        },
                        {
                            "type": "paragraph",
                            "text": "The API returns standard HTTP status codes. Error responses include a JSON object with error code and descriptive message to help with debugging."
                        }
                    ],
                    "font_size": 11
                }
            }
        }
    ],
    
    "excel_spreadsheet": [
        {
            "user_prompt": "Create a sales tracking spreadsheet with monthly data for different products and regions",
            "expected_tool_call": {
                "tool": "generate_excel_spreadsheet",
                "args": {
                    "title": "Sales Tracking Dashboard",
                    "sheets": [
                        {
                            "name": "Product Sales",
                            "headers": ["Product", "January", "February", "March", "Q1 Total", "Growth %"],
                            "data": [
                                ["Product A", 15000, 18000, 22000, 55000, "46.7%"],
                                ["Product B", 12000, 14500, 16800, 43300, "40.0%"],
                                ["Product C", 8500, 9200, 11000, 28700, "29.4%"],
                                ["Product D", 6000, 7500, 8200, 21700, "36.7%"],
                                ["Product E", 4200, 5100, 6300, 15600, "50.0%"]
                            ]
                        },
                        {
                            "name": "Regional Sales",
                            "headers": ["Region", "Q1 Sales", "Target", "Achievement %", "Top Product"],
                            "data": [
                                ["North America", 85000, 80000, "106.3%", "Product A"],
                                ["Europe", 62000, 65000, "95.4%", "Product B"],
                                ["Asia Pacific", 48000, 45000, "106.7%", "Product A"],
                                ["Latin America", 25000, 28000, "89.3%", "Product C"],
                                ["Middle East", 18000, 20000, "90.0%", "Product B"]
                            ]
                        },
                        {
                            "name": "Summary",
                            "headers": ["Metric", "Value", "Target", "Status"],
                            "data": [
                                ["Total Revenue", "$238,000", "$238,000", "On Target"],
                                ["Total Units Sold", "12,450", "12,000", "Above Target"],
                                ["Average Order Value", "$19.12", "$19.83", "Below Target"],
                                ["Customer Acquisition", "1,250", "1,200", "Above Target"],
                                ["Customer Retention", "94.5%", "95.0%", "Close to Target"]
                            ]
                        }
                    ],
                    "include_charts": false
                }
            }
        },
        {
            "user_prompt": "Generate a project budget spreadsheet with different categories, monthly breakdown, and totals",
            "expected_tool_call": {
                "tool": "generate_excel_spreadsheet",
                "args": {
                    "title": "Project Budget Analysis",
                    "sheets": [
                        {
                            "name": "Budget Breakdown",
                            "headers": ["Category", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Total"],
                            "data": [
                                ["Personnel", 25000, 25000, 25000, 25000, 25000, 25000, 150000],
                                ["Equipment", 15000, 5000, 2000, 3000, 1000, 2000, 28000],
                                ["Software Licenses", 3000, 500, 500, 500, 500, 500, 5500],
                                ["Marketing", 8000, 12000, 15000, 10000, 8000, 6000, 59000],
                                ["Travel", 2000, 3000, 1500, 2500, 1000, 1500, 11500],
                                ["Miscellaneous", 1000, 1500, 2000, 1000, 1500, 1000, 8000]
                            ]
                        },
                        {
                            "name": "Cost Centers",
                            "headers": ["Department", "Allocated Budget", "Spent to Date", "Remaining", "Utilization %"],
                            "data": [
                                ["Engineering", 80000, 65000, 15000, "81.3%"],
                                ["Marketing", 59000, 45000, 14000, "76.3%"],
                                ["Operations", 35000, 28000, 7000, "80.0%"],
                                ["Sales", 25000, 18000, 7000, "72.0%"],
                                ["Administration", 15000, 12000, 3000, "80.0%"]
                            ]
                        },
                        {
                            "name": "Variance Analysis",
                            "headers": ["Month", "Budgeted", "Actual", "Variance", "Variance %"],
                            "data": [
                                ["January", 54000, 52000, -2000, "-3.7%"],
                                ["February", 47000, 49000, 2000, "4.3%"],
                                ["March", 46000, 44000, -2000, "-4.3%"],
                                ["April", 42000, 41000, -1000, "-2.4%"],
                                ["May", 37000, 38000, 1000, "2.7%"],
                                ["June", 36000, 35000, -1000, "-2.8%"]
                            ]
                        }
                    ],
                    "include_charts": false
                }
            }
        }
    ]
}

def get_example_prompts():
    """Return example prompts for testing document generation tools"""
    return EXAMPLE_PROMPTS

def print_examples():
    """Print all example prompts for reference"""
    print("=== DOCUMENT GENERATION TOOL EXAMPLES ===\n")
    
    for doc_type, examples in EXAMPLE_PROMPTS.items():
        print(f"📄 {doc_type.upper()} EXAMPLES:")
        print("-" * 50)
        
        for i, example in enumerate(examples, 1):
            print(f"\n{i}. User Prompt:")
            print(f'   "{example["user_prompt"]}"')
            print(f"\n   Expected Tool: {example['expected_tool_call']['tool']}")
            print(f"   Title: {example['expected_tool_call']['args']['title']}")
            
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    print_examples()