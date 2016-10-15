# Duplicate Request (New Request based on same criteria)
DUPLICATE_REQUEST = 0x00001
# View detailed request status (Open, In Progress, Closed)
VIEW_REQUEST_STATUS_PUBLIC = 0x00002
# View detailed request status (Open, In Progress, Due Soon, Overdue, Closed)
VIEW_REQUEST_STATUS_ALL = 0x00004
# View all public request information
VIEW_REQUEST_INFO_PUBLIC = 0x00008
# View all request information
VIEW_REQUEST_INFO_ALL = 0x00010
# Add Note (Agency Only) or (Agency Only & Requester Only) or (Agency Only, Requester / Agency)
ADD_NOTE = 0x00020
# Upload Documents (Agency Only & Requester Only) or (Agency Only / Private) or
#   (Agency Only / Private, Agency / Requester, All Users)
UPLOAD_DOCUMENTS = 0x00040
# View Documents Immediately - Public or 'Released and Private'
VIEW_DOCUMENTS_IMMEDIATELY = 0x00080
# View requests where they are assigned
VIEW_REQUESTS_HELPER = 0x00100
# View all requests for their agency
VIEW_REQUESTS_AGENCY = 0x00200
# View all requests for all agencies
VIEW_REQUESTS_ALL = 0x00400
# Extend Request
EXTEND_REQUESTS = 0x00800
# Close Request (Denial/Fulfill)
CLOSE_REQUESTS = 0x01000
# Add Helper (Helper permissions must be specified on a per request basis)
ADD_HELPERS = 0x02000
# Remove Helper
REMOVE_HELPERS = 0x04000
# Acknowledge
ACKNOWLEDGE = 0x08000
# Change Request POC
CHANGE_REQUEST_POC = 0x10000
# All permissions
ADMINISTER = 0x20000
