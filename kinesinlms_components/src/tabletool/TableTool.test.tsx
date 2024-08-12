import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import '@testing-library/jest-dom'
import TableTool from './TableTool';

const server = setupServer();

describe('TableTool', () => {
    beforeAll(() => server.listen());
    afterEach(() => server.resetHandlers());
    afterAll(() => server.close());

    it('should POST on the first save and PUT on all following saves', async () => {
        let postCount = 0;
        let putCount = 0;
        server.use(
            http.post('/api/simple_interactive_tool_submissions', () => {
                postCount++;
                return HttpResponse.json({ id: 1 });
            }),
            http.put('/api/simple_interactive_tool_submissions/1', () => {
                putCount++;
                return HttpResponse.json({ id: 1 });
            }),
        );
        render(
            <TableTool
                course_id={1}
                course_unit_id={3}
                definition={{
                    allow_add_row: false,
                    allow_remove_row: false,
                    default_rows: [
                        { row_id: 1, cells: [] },
                        { row_id: 2, cells: [] },
                    ],
                    max_rows: 10,
                    initial_empty_rows: 1,
                    column_definitions: [
                        { column_id: 'a', header: 'A', default_cell_type: 'USER_ENTRY' },
                        { column_id: 'b', header: 'B', default_cell_type: 'USER_ENTRY' },
                    ],
                }}
                existing_simple_interactive_tool_submission={undefined}
                existing_simple_interactive_tool_submission_id={undefined}
                read_only={false}
                simple_interactive_tool_id={1}
                score={0}
                max_score={1}
            />
        );

        expect(postCount).toBe(0);
        expect(putCount).toBe(0);

        const textArea = screen.getByTestId('editable-cell-textarea-1-a');
        const saveBtn = screen.getByTestId('table-save-button');

        expect(saveBtn).toBeDisabled();
        expect(textArea).toBeEmptyDOMElement();

        fireEvent.change(textArea, { target: { value: "someText" } })
        fireEvent.change(textArea);

        expect(saveBtn).toBeDisabled();
        // Wait for the 200ms debounce to be done.
        await act(() => new Promise((r) => setTimeout(r, 300)));
        expect(saveBtn).not.toBeDisabled();

        fireEvent.click(saveBtn);
        await waitFor(() => screen.getByTestId('saving-notice'));

        expect(postCount).toBe(1);
        expect(putCount).toBe(0);

        fireEvent.change(textArea, { target: { value: "some other text" } })
        // Wait for the 200ms debounce to be done.
        await act(() => new Promise((r) => setTimeout(r, 300)));

        fireEvent.click(saveBtn);
        await waitFor(() => screen.getByTestId('saving-notice'));

        expect(postCount).toBe(1);
        expect(putCount).toBe(1);

        fireEvent.change(textArea, { target: { value: "some final text" } })
        // Wait for the 200ms debounce to be done.
        await act(() => new Promise((r) => setTimeout(r, 300)));

        fireEvent.click(saveBtn);
        await waitFor(() => screen.getByTestId('saving-notice'));

        expect(postCount).toBe(1);
        expect(putCount).toBe(2);
    });
});
