{
    'name': 'T-One Portal',
    'version': '1.0',
    'summary': 'Add a custom landing page for T-One Portal.',
    'description': 'Add a custom landing page for T-One Portal with quick access buttons.',
    'category': 'Website/Portal',
    'author': 'SOCIUS-IGB',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'website',
        'portal',
        'products_rma'
    ],
    'data': [
        'views/custom_portal.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            't_one_portal/static/src/css/landing_page.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
