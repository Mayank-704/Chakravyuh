import docker
import os
import time
import tarfile

class DockerTrapSpawner:
    """
    Spawns a Docker container to act as a trap for attackers.
    """
    def __init__(self):
        self.client = docker.from_env()

    def deploy_trap(self, institution_type):
        """
        Pulls a Docker image and starts a container.
        """
        print(f"Deploying trap for institution type: {institution_type}")
        try:
            print("Pulling 'ubuntu' image...")
            self.client.images.pull('ubuntu')
            print("Image pulled.")
            container = self.client.containers.run('ubuntu', detach=True, tty=True)
            print(f"Container {container.id} started.")
            return container
        except docker.errors.APIError as e:
            print(f"Docker API error: {e}")
            return None

class SyntheticDataInjector:
    """
    Injects synthetic data into a Docker container.
    """
    def __init__(self, base_path='backend/federated/fake_data'):
        self.base_path = base_path

    def _create_tar(self, path, dest_path):
        """Creates a tar archive of a file to be copied into the container."""
        pw_tar = tarfile.open('temp.tar', 'w')
        pw_tar.add(path, arcname=os.path.basename(dest_path))
        pw_tar.close()
        with open('temp.tar', 'rb') as f:
            return f.read()

    def inject_data(self, container, institution_type):
        """
        Copies fake data into the specified container based on institution type.
        """
        data_path = os.path.join(self.base_path, institution_type)
        if not os.path.isdir(data_path):
            print(f"Data directory not found for institution type: {institution_type}")
            return

        print(f"Injecting data for {institution_type} into container {container.id}")
        for item in os.listdir(data_path):
            src_path = os.path.join(data_path, item)
            dest_path = f'/root/{item}' 
            
            # Create a tarball in memory
            with tarfile.open('temp.tar', 'w') as tar:
                tar.add(src_path, arcname=item)
            
            with open('temp.tar', 'rb') as f:
                data = f.read()

            container.put_archive(os.path.dirname(dest_path), data)
            print(f"  - Injected {item} into {dest_path}")
        
        # Clean up temp tar file
        if os.path.exists('temp.tar'):
            os.remove('temp.tar')


def simulate_attack(institution_type):
    """
    Simulates the full process of deploying a trap and injecting data.
    """
    print("-" * 50)
    print(f"Simulating attack on a {institution_type}")
    print("-" * 50)

    spawner = DockerTrapSpawner()
    trap_container = spawner.deploy_trap(institution_type)

    if trap_container:
        injector = SyntheticDataInjector()
        injector.inject_data(trap_container, institution_type)

        print("\nAttacker is now in the trap. Monitoring commands...")
        # In a real scenario, we would redirect the attacker's connection here
        # and log their commands. For this simulation, we'll just show the container is running.
        try:
            print("Trap active for 30 seconds...")
            for i in range(30):
                time.sleep(1)
                print(f"  (running... {30-i}s left)", end='\r')
            print("\nSession ended.")
        finally:
            print("Stopping and removing trap container.")
            trap_container.stop()
            trap_container.remove()
            print("Trap dismantled.")

if __name__ == '__main__':
    # Simulate attacks on different institution types
    simulate_attack('hospital')
    simulate_attack('bank')
    simulate_attack('government')
