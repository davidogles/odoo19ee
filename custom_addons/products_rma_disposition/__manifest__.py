{
    'name': 'RMA Disposition Management',
    'version': '19.0.0',
    'summary': 'Add disposition tracking for RMA products with stock operations',
    'category': 'Inventory/Inventory',
    'author': 'SOCIUS-IGB',
    'license': 'LGPL-3',
    'depends': [
        'products_rma',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/disposal_reason_data.xml',
        'views/helpdesk_rma_disposition_views.xml',
        'views/disposal_reason_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
