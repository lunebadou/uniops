import docker

client = docker.from_env()

print("=== Conteneurs en cours d'exécution ===\n")

for container in client.containers.list():
    stats = container.stats(stream=False)  # snapshot unique

    # Calcul CPU (formule officielle Docker)
    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
    system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]
    cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0

    # Mémoire
    mem_usage_mb = stats["memory_stats"].get("usage", 0) / (1024 * 1024)
    mem_limit_mb = stats["memory_stats"].get("limit", 1) / (1024 * 1024)

    print(f"📦 {container.name}")
    print(f"   Image  : {container.image.tags[0] if container.image.tags else 'untagged'}")
    print(f"   Status : {container.status}")
    print(f"   CPU    : {cpu_percent:.2f} %")
    print(f"   RAM    : {mem_usage_mb:.1f} MB / {mem_limit_mb:.0f} MB")
    print()