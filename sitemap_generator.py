from main import app
from acpool.models import db, Coins

with app.app_context():
    coins = db.session.query(Coins).filter(Coins.open.is_(True)).all()

    print(len(coins))
    with open('templates/sitemap.xml', 'w') as sitemap:
        sitemap.writelines('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        sitemap.writelines('<url><loc>https://acpool.me</loc></url>\n')
        sitemap.writelines('<url><loc>https://acpool.me/wallet</loc></url>\n')
        sitemap.writelines('<url><loc>https://acpool.me/login</loc></url>\n')
        sitemap.writelines('<url><loc>https://acpool.me/signup</loc></url>\n')

        for item in coins:
            sitemap.writelines('<url><loc>https://acpool.me/coin/%s</loc></url>\n' % item.name)

        sitemap.writelines('</urlset>')
