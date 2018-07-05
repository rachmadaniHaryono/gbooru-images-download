from flask_restful import Resource


class HydrusResource(Resource):
    """Hydrus resource."""
    def get(self, search_query_id=None):
        """Get search query result tailored for hydrus.

        ---
        parameters:
        - in: path
          name: search_query_id
          type: string
          required: True
        responses:
          200:
            description: Search query result.
            schema:
              id: SearchQuery
              properties:
                search_term:
                    type: string
                    description: Search term.
                page:
                    type: integer
                    description: Page.
                    min: 1
                match_results:
                    type: object
                    description: Match results.
              required:
                - search_term
                - page
        """
        pass

    def post(self, query, page=1):
        pass
