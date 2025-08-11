# Guide de Déploiement SilenCut Web

## 🚀 Lancement Local

### Méthode 1 : Script Shell
```bash
./run_webapp.sh
```
Puis ouvrir http://localhost:8000

### Méthode 2 : Docker
```bash
docker-compose up --build
```

### Méthode 3 : Manuel
```bash
source venv/bin/activate
pip install -r webapp/requirements.txt
python -m uvicorn webapp.app:app --reload --port 8000
```

## 🌐 Déploiement Production

### Option 1 : VPS (Hetzner, OVH, DigitalOcean)

1. **Préparer le serveur** (Ubuntu 22.04)
```bash
# Connexion SSH
ssh root@your-server-ip

# Mise à jour système
apt update && apt upgrade -y

# Installer dépendances
apt install -y python3-pip python3-venv ffmpeg nginx certbot python3-certbot-nginx git

# Cloner le projet
git clone https://github.com/yourusername/silencut.git
cd silencut

# Environnement virtuel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r webapp/requirements.txt
pip install gunicorn
```

2. **Configurer Systemd**
```bash
# Créer /etc/systemd/system/silencut.service
[Unit]
Description=SilenCut Web Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/silencut
Environment="PATH=/opt/silencut/venv/bin"
ExecStart=/opt/silencut/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker webapp.app:app --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

3. **Configurer Nginx**
```nginx
server {
    listen 80;
    server_name silencut.example.com;
    client_max_body_size 500M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

4. **SSL avec Let's Encrypt**
```bash
certbot --nginx -d silencut.example.com
```

5. **Démarrer les services**
```bash
systemctl start silencut
systemctl enable silencut
systemctl restart nginx
```

### Option 2 : Docker sur VPS

```bash
# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose
apt install docker-compose

# Cloner et lancer
git clone https://github.com/yourusername/silencut.git
cd silencut
docker-compose up -d
```

### Option 3 : Render.com (Gratuit/Payant)

1. Créer un compte sur [Render.com](https://render.com)
2. Nouveau Web Service
3. Connecter GitHub repo
4. Configuration :
   - Build Command: `pip install -r requirements.txt && pip install -r webapp/requirements.txt`
   - Start Command: `uvicorn webapp.app:app --host 0.0.0.0 --port $PORT`
   - Ajouter FFmpeg dans le Dockerfile

### Option 4 : Railway.app

1. Installer Railway CLI
```bash
npm i -g @railway/cli
```

2. Déployer
```bash
railway login
railway init
railway add
railway up
```

### Option 5 : Google Cloud Run

```bash
# Build et push l'image
gcloud builds submit --tag gcr.io/PROJECT-ID/silencut

# Déployer
gcloud run deploy --image gcr.io/PROJECT-ID/silencut --platform managed
```

## 🔒 Sécurité Production

1. **Limites de taille** : Ajuster MAX_FILE_SIZE
2. **Rate limiting** : Ajouter slowapi
3. **Authentication** : Implémenter JWT si nécessaire
4. **CORS** : Limiter aux domaines autorisés
5. **Storage** : Utiliser S3/GCS pour les fichiers
6. **Queue** : Redis + Celery pour scalabilité

## 📊 Monitoring

1. **Logs** : Utiliser Sentry ou LogDNA
2. **Metrics** : Prometheus + Grafana
3. **Uptime** : UptimeRobot ou Pingdom

## 💰 Monétisation

### Freemium Model
- **Gratuit** : 5 vidéos/jour, max 100MB, max 5 min
- **Pro** : 14.99€/mois, illimité
- **API** : 49.99€/mois

### Implémentation Stripe
```python
# webapp/payments.py
import stripe

stripe.api_key = "sk_..."

def create_checkout_session():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': 'price_...',
            'quantity': 1,
        }],
        mode='subscription',
        success_url='https://silencut.com/success',
        cancel_url='https://silencut.com/cancel',
    )
    return session
```

## 🚀 Scaling

### Architecture Scalable
```
                    ┌─────────────┐
                    │   Cloudflare│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Load Balancer│
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐    ┌─────▼─────┐   ┌─────▼─────┐
    │  Worker 1 │    │  Worker 2 │   │  Worker 3 │
    └─────┬─────┘    └─────┬─────┘   └─────┬─────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │   (Queue)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │     S3      │
                    │  (Storage)  │
                    └─────────────┘
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: silencut
spec:
  replicas: 3
  selector:
    matchLabels:
      app: silencut
  template:
    metadata:
      labels:
        app: silencut
    spec:
      containers:
      - name: silencut
        image: silencut:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

## 📝 Checklist Pré-Production

- [ ] Tests unitaires et d'intégration
- [ ] Gestion d'erreurs robuste
- [ ] Logs structurés
- [ ] Backup automatique
- [ ] Monitoring des performances
- [ ] Documentation API
- [ ] Terms of Service / Privacy Policy
- [ ] GDPR compliance
- [ ] SSL/TLS configuré
- [ ] Firewall configuré
- [ ] Secrets dans variables d'environnement
- [ ] CI/CD pipeline (GitHub Actions)

## 🆘 Support

Pour toute question : github.com/yourusername/silencut/issues