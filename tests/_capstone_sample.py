"""
Structural excerpt of a real `processSdpAttendance` response.

Trimmed to a few calendar rows but otherwise verbatim, including the
commented-out Thymeleaf info table and the commented-out Description
column that are both present in the live response.
"""

CAPSTONE_RESPONSE = '''<div id="sdpAttendanceFragment">
    <div class="modal" id="sdpAttendanceModal">
        <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable" style="max-width: 70%;">
            <div class="modal-content">
                <div class="modal-header">
                    <h4 class="modal-title" style="font-weight: bold; text-decoration: underline;">
                        CAPSTONE/SDP Attendance Detail
                    </h4>
                </div>
                <!-- <div class="modal-body">
                    <table class="table table-bordered">
                        <tr>
                            <th style="width: 25%;">Title</th>
                            <td style="width: 75%;" th:text="${title}"></td>
                        </tr>
                        <tr>
                            <th>Guide Evaluation Status</th>
                            <td>
                                <span th:if="${status == 0}" class="badge bg-danger">Rejected</span>
                                <span th:if="${status == 1}" class="badge bg-success">Approved</span>
                                <span th:if="${status == 2}" class="badge bg-warning text-dark">Pending</span>
                            </td>
                        </tr>
                        <tr>
                            <th>Date of Registration</th>
                            <td th:text="${dateOfRegistered}"></td>
                        </tr>
                    </table>
                </div> -->
                <div class="modal-body">
											<table class="table table-bordered">
												<tr>
													<th style="width: 25%;">Title</th>
													<td style="width: 75%;">Capstone</td>
												</tr>
												<tr>
													<th>Guide Evaluation Status</th>
													<td><span>Registered, Invoice Generated, Approved by Academics and Faculty</span></td>
												</tr>
												<tr>
													<th>Date of Registration</th>
													<td>2026-07-06 00:00:00.0</td>
												</tr>
											</table>
										</div>
                <div class="modal-body">
                    <h5 style="font-weight: bold; text-decoration: underline;">Attendance Summary</h5>
                    <table class="table table-bordered text-center">
                        <thead>
                            <tr style="background-color: #3c8dbc; color: #fff;">
                                <th style="width: 12%;">Present</th>
                                <th style="width: 12%;">On Duty (OD)</th>
                                <th style="width: 12%;">Absent</th>
                                <th style="width: 12%;">Percentage</th>
                                <th style="width: 15%;">Punch Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="color: green; font-weight: bold;">14</td>
                                <td style="color: blue; font-weight: bold;">4</td>
                                <td style="color: red; font-weight: bold;">12</td>
                                <td>
                                    <span style="color: red; font-size: 18px; font-weight: bold;">60%</span>
                                </td>
                                <td>
                                    <a href="#" data-bs-toggle="collapse" data-bs-target="#punchDetailsCollapse"
                                       style="text-decoration: none; color: #3c8dbc; font-weight: bold;">
                                       <span class="glyphicon glyphicon-eye-open"></span> View
                                    </a>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    <div class="collapse mt-3" id="punchDetailsCollapse">
                        <div class="card card-body">
                            <h6 style="font-weight: bold; color: #3c8dbc;">
                                Punch Details Upto Today
                            </h6>
                            <table id="sdpCalendarTable" class="table table-bordered table-hover">
                                <thead>
                                    <tr style="background-color: #2471a3; color: white; text-align: center;">
                                        <th style="width: 8%;">Sl.No.</th>
                                        <th style="width: 12%;">Date</th>
                                        <th style="width: 12%;">Day</th>
                                        <th style="width: 15%;">Day Type</th>
<!--                                         <th style="width: 25%;">Description</th>  -->
                                      <th style="width: 13%;">Status</th>
                                        <th style="width: 15%;">Punch Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td align="center">1</td>
                                        <td align="center">17-07-2026</td>
                                        <td align="center">FRIDAY</td>
                                        <td align="center">Instructional</td>
<!--                                         <td th:text="${entry.description}"></td>  -->
                                       <td align="center">
                                            <span>

                                                <span style="color: red; font-weight: bold;">Absent</span>


                                            </span>
                                        </td>
                                        <td align="center">

                                            <span>-</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center">3</td>
                                        <td align="center">19-07-2026</td>
                                        <td align="center">SUNDAY</td>
                                        <td align="center">Holiday</td>
<!--                                         <td th:text="${entry.description}"></td>  -->
                                       <td align="center">
                                            <span>



                                                 <span>-</span>
                                            </span>
                                        </td>
                                        <td align="center">

                                            <span>-</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center">4</td>
                                        <td align="center">20-07-2026</td>
                                        <td align="center">MONDAY</td>
                                        <td align="center">No Instructional</td>
<!--                                         <td th:text="${entry.description}"></td>  -->
                                       <td align="center">
                                            <span>



                                                 <span>-</span>
                                            </span>
                                        </td>
                                        <td align="center">

                                            <span>-</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center">9</td>
                                        <td align="center">25-07-2026</td>
                                        <td align="center">SATURDAY</td>
                                        <td align="center">Instructional</td>
<!--                                         <td th:text="${entry.description}"></td>  -->
                                       <td align="center">
                                            <span>


                                                <span style="color: blue; font-weight: bold;">On Duty</span>

                                            </span>
                                        </td>
                                        <td align="center">

                                            <span>-</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center">19</td>
                                        <td align="center">04-08-2026</td>
                                        <td align="center">TUESDAY</td>
                                        <td align="center">Instructional</td>
<!--                                         <td th:text="${entry.description}"></td>  -->
                                       <td align="center">
                                            <span>
                                                <span style="color: green; font-weight: bold;">Present</span>


                                            </span>
                                        </td>
                                        <td align="center">
                                            <span style="color: green; font-weight: bold;">09:49:13</span>

                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center">32</td>
                                        <td align="center">17-08-2026</td>
                                        <td align="center">MONDAY</td>
                                        <td align="center">CAT1</td>
<!--                                         <td th:text="${entry.description}"></td>  -->
                                       <td align="center">
                                            <span>



                                                 <span>-</span>
                                            </span>
                                        </td>
                                        <td align="center">

                                            <span>-</span>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" type="button" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>
</div>
'''
