from neo4j import GraphDatabase
import pandas as pd
import ast


uri = "bolt://localhost:7687"
username = "neo4j"
password = "David1234"
driver = GraphDatabase.driver(uri, auth=(username, password))


def test_connection():
    with driver.session() as session:
        result = session.run("RETURN 'Connection Successful' AS message")
        for record in result:
            print(record["message"])


data = pd.read_csv('data/credits.csv', nrows=50) 
data['cast'] = data['cast'].apply(ast.literal_eval)
data['crew'] = data['crew'].apply(ast.literal_eval)


cast_data = []
for index, row in data.iterrows():
    for cast in row['cast']:
        cast_data.append({
            "actor_id": cast['id'],
            "name": cast['name'],
            "character": cast.get('character', None),
            "movie_id": row['id']
        })
cast_df = pd.DataFrame(cast_data)


crew_data = []
for index, row in data.iterrows():
    for crew in row['crew']:
        crew_data.append({
            "crew_id": crew['id'],
            "name": crew['name'],
            "job": crew['job'],
            "department": crew['department'],
            "movie_id": row['id']
        })
crew_df = pd.DataFrame(crew_data)

# Create Ontology and Taxonomy
def create_ontology_and_taxonomy():
    with driver.session() as session:

        session.execute_write(
            lambda tx: tx.run("""
            MERGE (:Class {name: 'Person'})
            MERGE (:Class {name: 'Actor'})-[:IS_A]->(:Class {name: 'Person'})
            MERGE (:Class {name: 'Crew'})-[:IS_A]->(:Class {name: 'Person'})
            MERGE (:Class {name: 'Movie'})
            """)
        )

        session.execute_write(
            lambda tx: tx.run("""
            MERGE (:Department {name: 'Production'})
            MERGE (:Department {name: 'Directing'})
            MERGE (:Department {name: 'Writing'})
            MERGE (:Department {name: 'Editing'})
            MERGE (:Department {name: 'Sound'})
            MERGE (:Department {name: 'Visual Effects'})
            """)
        )
        print("Ontology and taxonomy nodes created!")


def create_nodes_and_relationships():
    with driver.session() as session:
        for _, row in data.iterrows():
            session.execute_write(
                lambda tx: tx.run("""
                MERGE (m:Movie {id: $id})
                """, {"id": row['id']})
            )
        
        for _, row in cast_df.iterrows():
            session.execute_write(
                lambda tx: tx.run("""
                MERGE (a:Actor {id: $actor_id, name: $name})
                MERGE (a)-[:IS_A]->(:Person)
                MERGE (m:Movie {id: $movie_id})
                MERGE (a)-[:ACTED_IN {character: $character}]->(m)
                """, {
                    "actor_id": row['actor_id'], 
                    "name": row['name'], 
                    "movie_id": row['movie_id'], 
                    "character": row['character']
                })
            )
        
        for _, row in crew_df.iterrows():
            session.execute_write(
                lambda tx: tx.run("""
                MERGE (c:Crew {id: $crew_id, name: $name, job: $job, department: $department})
                MERGE (c)-[:IS_A]->(:Person)
                MERGE (d:Department {name: $department})
                MERGE (c)-[:WORKS_IN]->(d)
                MERGE (m:Movie {id: $movie_id})
                MERGE (c)-[:WORKED_ON {job: $job}]->(m)
                """, {
                    "crew_id": row['crew_id'], 
                    "name": row['name'], 
                    "job": row['job'], 
                    "department": row['department'], 
                    "movie_id": row['movie_id']
                })
            )
        print("Nodes and relationships created successfully!")

def print_ontology():
    with driver.session() as session:
        result = session.run("""
        MATCH (subclass:Class)-[:IS_A]->(superclass:Class)
        RETURN subclass.name AS Subclass, superclass.name AS Superclass
        """)
        print("\nOntology Structure:")
        for record in result:
            print(f"{record['Subclass']} IS_A {record['Superclass']}")

def print_taxonomy():
    with driver.session() as session:
        result = session.run("""
        MATCH (c:Crew)-[:WORKS_IN]->(d:Department)
        RETURN c.name AS CrewMember, c.job AS Job, d.name AS Department
        LIMIT 10
        """)
        print("\nTaxonomy Structure:")
        for record in result:
            print(f"{record['CrewMember']} ({record['Job']}) WORKS_IN {record['Department']}")


def print_actor_movie_relationships():
    with driver.session() as session:
        result = session.run("""
        MATCH (a:Actor)-[r:ACTED_IN]->(m:Movie)
        RETURN a.name AS Actor, m.id AS MovieID, r.character AS Character
        LIMIT 10
        """)
        print("\nActors and Movies:")
        for record in result:
            print(f"Actor: {record['Actor']}, Movie ID: {record['MovieID']}, Character: {record['Character']}")


def print_crew_movie_relationships():
    with driver.session() as session:
        result = session.run("""
        MATCH (c:Crew)-[r:WORKED_ON]->(m:Movie)
        RETURN c.name AS CrewMember, m.id AS MovieID, r.job AS Job
        LIMIT 10
        """)
        print("\nCrew and Movies:")
        for record in result:
            print(f"Crew Member: {record['CrewMember']}, Movie ID: {record['MovieID']}, Job: {record['Job']}")


  

if __name__ == "__main__":

    test_connection()
    create_ontology_and_taxonomy()
    create_nodes_and_relationships()
    
    print("\nPrinting Ontology...")
    print_ontology()
    
    print("\nPrinting Taxonomy...")
    print_taxonomy()
    
    driver.close()

