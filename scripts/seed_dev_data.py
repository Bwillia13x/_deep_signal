from app.db.models.paper import Paper
from app.db.models.repository import Repository
from app.db.session import SessionLocal

sample_papers = [
    {
        "external_id": "arxiv:2401.00001",
        "title": "Emerging foundations of soft robotics",
        "abstract": "Investigating new materials for soft actuators",
        "domain": "cs.RO",
        "keywords": ["soft robotics", "actuators"],
    },
    {
        "external_id": "arxiv:2401.00002",
        "title": "Graph neural symbolic solvers",
        "abstract": "Combining symbolic reasoning with graph embeddings",
        "domain": "cs.AI",
        "keywords": ["graph neural nets", "symbolic"],
    },
]

sample_repos = [
    {
        "full_name": "deeptech-labs/soft-actuator",
        "description": "Control stack for soft actuators with OpenVINO",
        "language": "Python",
        "topics": ["robotics", "soft-robotics", "control"],
    },
    {
        "full_name": "deeptech-labs/graph-symbolic",
        "description": "Graph neural symbolic reasoning scaffolding",
        "language": "Python",
        "topics": ["graph", "ML", "symbolic"],
    },
]


def main() -> None:
    session = SessionLocal()
    try:
        for paper_data in sample_papers:
            if (
                not session.query(Paper)
                .filter_by(external_id=paper_data["external_id"])
                .first()
            ):
                session.add(Paper(**paper_data))
        for repo_data in sample_repos:
            if (
                not session.query(Repository)
                .filter_by(full_name=repo_data["full_name"])
                .first()
            ):
                session.add(Repository(**repo_data))
        session.commit()
        print("Seed data inserted")
    finally:
        session.close()


if __name__ == "__main__":
    main()
