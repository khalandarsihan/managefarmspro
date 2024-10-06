name: CD Pipeline

on:
  push:
    branches:
      - develop

jobs:
  build-and-deploy:
    name: Build Docker Image and Deploy
    runs-on: ubuntu-latest

    steps:
      # Checkout the repository
      - name: Checkout repository
        uses: actions/checkout@v3

      # Generate Version Number for Tagging
      - name: Generate Version Number
        run: |
          version=$(date +"%Y%m%d%H%M%S")
          echo "version=$version" >> $GITHUB_ENV

      # Set up Docker Buildx for Multi-platform Support
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v1

      # Login to GitHub Container Registry (ghcr.io)
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v1
        with:
          registry: ghcr.io
          username: ${{ github.repository_owner }}
          password: ${{ secrets.MY_PAT_SECRET }}

      # Build the Docker Image Using Containerfile and Push to GitHub Container Registry
      - name: Build and Push Docker Image
        run: |
          docker buildx build \
            --platform linux/amd64 \
            --build-arg FRAPPE_REPO=https://github.com/khalandarsihan/frappe.git \
            --build-arg FRAPPE_BRANCH=version-15 \
            --build-arg ERPNEXT_REPO=https://github.com/khalandarsihan/erpnext.git \
            --build-arg ERPNEXT_BRANCH=version-15 \
            --build-arg PAYMENTS_REPO=https://github.com/khalandarsihan/payments.git \
            --build-arg PAYMENTS_BRANCH=version-15 \
            --build-arg MANAGEFARMSPRO_REPO=https://github.com/khalandarsihan/managefarmspro.git \
            --build-arg MANAGEFARMSPRO_BRANCH=develop \
            -t ghcr.io/${{ github.repository_owner }}/managefarmspro:${{ env.version }} \
            -t ghcr.io/${{ github.repository_owner }}/managefarmspro:latest \
            --push \
            -f Containerfile .

      # Deploy to Staging Server
      - name: Deploy to Staging
        uses: appleboy/ssh-action@v0.1.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USERNAME }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            export CUSTOM_IMAGE="ghcr.io/${{ github.repository_owner }}/managefarmspro"
            export CUSTOM_TAG="${{ env.version }}"
            echo "CUSTOM_IMAGE=${CUSTOM_IMAGE}"
            echo "CUSTOM_TAG=${CUSTOM_TAG}"
            sed -i "s|ghcr.io/khalandarsihan/managefarmspro/frappe-app:.*|${CUSTOM_IMAGE}:${CUSTOM_TAG}|g" /home/sihan/staging/frappe_docker/pwd.yml
            cd /home/sihan/staging/frappe_docker
            docker compose -f pwd.yml down
            docker system prune -af    # Docker pruning after docker compose down
            docker volume prune -f     # Volume pruning after docker compose down
            docker compose -f pwd.yml pull
            docker compose -f pwd.yml up -d
            sleep 300
            if curl -s -o /dev/null -w "%{http_code}" https://khasihan.xyz | grep 200; then
              echo "Deployment successful!"
            else
              echo "Deployment failed"
              exit 1


