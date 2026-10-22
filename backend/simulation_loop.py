import time
import threading
import concurrent.futures
from .simulation_state import WorldState
from .agent.agent import VillagerAgent


class BackendSimulation:
    def __init__(self, state: WorldState, llm_client):
        self.state = state
        self.llm_client = llm_client
        self.running = True
        self.pending_requests = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.future = None
        self.MAX_BATCH_SIZE = 2         

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def queue_agent(self, villager_id, agent, context):
        self.pending_requests[villager_id] = (villager_id, agent, context)

    def is_queued(self, villager_id):
        return villager_id in self.pending_requests

    def _run(self):
        while self.running:
            # Deliver finished results to the frontend first so it can render
            if self.future and self.future.done():
                try:
                    results = self.future.result()
                    with self.state.lock:
                        if self.state.is_data_ready:
                            self.state.new_actions.update(results)
                        else:
                            self.state.new_actions = results
                        self.state.is_data_ready = True
                except Exception as e:
                    print(f"Backend API Error: {e}")
                self.future = None

            if self.pending_requests and self.future is None:

                # Queue for agents.
                items = list(self.pending_requests.items())[:self.MAX_BATCH_SIZE]
                for key, _ in items:
                    del self.pending_requests[key]
                batch = [v for _, v in items]
                
                print(f"[Backend] Flushing sub-batch of {len(batch)}/{len(batch) + len(self.pending_requests)} queued...")
                
                self.future = self.executor.submit(
                    VillagerAgent.decide_batch, batch, self.llm_client
                )

            # Tiny sleep to prevent the background thread from eating 100% of a CPU core
            time.sleep(0.05)